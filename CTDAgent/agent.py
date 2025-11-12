"""ReAct 스타일 CTD 에이전트 (ctdmate 통합)"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_community.chat_models import ChatLlamaCpp
from langchain_core.messages import HumanMessage
from registry import TOOLS, TOOL_SPEC
from settings import (
    LLAMA_MODEL_PATH, LLAMA_CTX, LLAMA_THREADS, LLAMA_MAX_TOKENS, LOG_LEVEL
)

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("ctd-react-agent")

SYSTEM_PROMPT = f"""당신은 CTD 문서 생성 및 검증을 위한 ReAct 스타일 에이전트입니다.

**⚠️  중요: 한 번에 하나의 Action만 출력하세요!**
**⚠️  Action 실행 후 Observation을 기다려야 합니다!**
**⚠️  여러 개의 Action을 동시에 출력하지 마세요!**

다음 도구들만 사용하세요 (반드시 JSON 형식으로 지시):
{json.dumps(TOOL_SPEC, ensure_ascii=False, indent=2)}

반드시 아래 형식을 따르세요:
Thought: (다음에 무엇을 할지 한 줄)
Action: {{ "tool": "<tool_name>", "args": {{ ... }} }}

그 다음 Observation을 기다리세요. Observation이 오면:
Thought: (다음 단계 계획)
Action: {{ "tool": "<next_tool>", "args": {{ ... }} }}

모든 작업이 완료되면:
FinalAnswer: (최종 결과)

작업 모드는 자동으로 판단됩니다:
- **생성 모드 (generate)**: Excel 파일 (.xlsx) → CTD 문서 생성
- **검증 모드 (validate)**: PDF 파일 (.pdf) → ICH 스키마 준수 검증

### [검증 모드] 워크플로우 (PDF 파일) - 반드시 순서대로 한 단계씩:
**Step 1:**
Thought: PDF 파일을 먼저 파싱해야 함
Action: {{ "tool": "parse_documents", "args": {{ "file_paths": [...] }} }}
(Observation 기다림)

**Step 2:**
Thought: 파싱된 내용을 검증해야 함
Action: {{ "tool": "generate_validation_report", "args": {{ "output_dir": "output", "output_format": "markdown" }} }}
(Observation 기다림)

**Step 3:**
FinalAnswer: 검증 완료

### [생성 모드] 워크플로우 (Excel 파일) - 반드시 순서대로 한 단계씩:
**Step 1:**
Thought: Excel에서 모듈을 생성해야 함
Action: {{ "tool": "generate_all_modules", "args": {{ "excel_path": "...", "output_dir": "output" }} }}
(Observation 기다림)

**Step 2:**
Thought: 생성된 YAML을 PDF로 변환해야 함
Action: {{ "tool": "save_as_pdf", "args": {{ "output_dir": "output" }} }}
(Observation 기다림)

**Step 3:**
FinalAnswer: PDF 경로

**절대 금지 사항:**
- 한 번에 여러 Action 출력 금지
- Action 다음에 바로 FinalAnswer 출력 금지
- Observation 없이 다음 Action 출력 금지
- 존재하지 않는 tool (예: "ReAct") 호출 금지
"""


def _extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """텍스트에서 도구 호출 추출 (첫 번째만)"""
    # Action: 이후의 첫 번째 JSON만 추출
    # 먼저 코드 블록 형식 시도
    m = re.search(r"Action:\s*```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if not m:
        # Action: 이후부터 시작하는 JSON 찾기 (중괄호 카운팅으로 완전한 JSON 추출)
        action_match = re.search(r'Action:\s*(\{)', text, flags=re.S)
        if not action_match:
            return None

        # Action: 이후부터 텍스트 추출
        start_pos = action_match.start(1)
        json_text = text[start_pos:]

        # 중괄호 개수를 세어 완전한 JSON 추출
        brace_count = 0
        end_pos = 0
        for i, char in enumerate(json_text):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i + 1
                    break

        if end_pos == 0:
            return None

        json_str = json_text[:end_pos]
    else:
        json_str = m.group(1)

    try:
        return json.loads(json_str)
    except Exception as e:
        log.warning(f"Failed to parse tool call: {e}")
        log.warning(f"JSON string was: {json_str[:200]}...")
        return None


def _run_tool(tool_obj: Any, args: Dict[str, Any], state: Dict[str, Any]) -> Any:
    """도구 실행"""
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(args)
    try:
        return tool_obj(args, state)
    except TypeError:
        try:
            return tool_obj(**(args or {}))
        except TypeError:
            return tool_obj()


def _detect_mode(file_paths: Optional[List[str]], texts: Optional[List[str]], llama=None) -> str:
    """
    입력을 분석하여 작업 모드를 자동 판단

    1차 판단: 파일명 키워드 (명시적 의도)
    2차 판단: 확장자 기반 (PDF → 검증, Excel → 생성)
    3차 판단: LLM 분석 (불확실한 경우만)

    Returns:
        "generate" | "validate"
    """
    file_paths = file_paths or []
    texts = texts or []

    # 1단계: 파일명 키워드 우선 확인 (명확한 사용자 의도)
    for path in file_paths:
        path_lower = path.lower()

        # 검증 모드 키워드 (파일명에 명시된 경우)
        validate_keywords = ["review", "check", "validate", "verify", "inspect", "final", "완성", "submitted", "approved","complete","CTD"]
        if any(keyword in path_lower for keyword in validate_keywords):
            log.info(f"🎯 Mode detection: 'validate' (filename keyword)")
            return "validate"

        # 생성 모드 키워드 (파일명에 명시된 경우)
        generate_keywords = ["template", "blank", "new", "draft", "초안", "템플릿", "empty","실험","연구","data","결과","자료","정보"]
        if any(keyword in path_lower for keyword in generate_keywords):
            log.info(f"🎯 Mode detection: 'generate' (filename keyword)")
            return "generate"

    # 텍스트 키워드 분석
    for text in texts:
        text_lower = text.lower()
        validate_keywords = ["ctd","국제공통기술문서","common technical document","목차","1부","2부","3부"]
        if any(keyword in text_lower for keyword in validate_keywords):
            log.info(f"🎯 Mode detection: 'validate' (text keyword)")
            return "validate"

    # 2단계: 확장자 기반 판단 (일반적인 사용 패턴)
    for path in file_paths:
        path_lower = path.lower()

        # PDF는 기본적으로 검증 모드 (완성된 문서)
        if path_lower.endswith(".pdf"):
            log.info(f"🎯 Mode detection: 'validate' (PDF extension - assumed complete document)")
            return "validate"

        # Excel은 기본적으로 생성 모드 (원시 데이터)
        if path_lower.endswith((".xlsx", ".xls", ".csv")):
            log.info(f"🎯 Mode detection: 'generate' (Excel extension - assumed raw data)")
            return "generate"

    # 3단계: LLM 분석 (확장자만으로 판단 어려운 경우)
    # 현재는 확장자 기반으로 충분하므로 LLM 분석은 선택적으로만 사용
    # if llama and file_paths:
    #     ... (주석 처리)

    # 기본값: 생성 모드
    log.info(f"🎯 Mode detection: 'generate' (default)")
    return "generate"


def run_agent(file_paths=None, texts=None, max_steps: int = 10) -> Dict[str, Any]:
    """
    ReAct 에이전트 실행

    Args:
        file_paths: 입력 파일 경로 리스트
        texts: 입력 텍스트 리스트
        max_steps: 최대 실행 스텝

    Returns:
        실행 결과 딕셔너리
    """
    state: Dict[str, Any] = {}

    # Llama 모델 로드
    log.info("┏" + "━"*78 + "┓")
    log.info("┃ 🧠 LOADING LLAMA MODEL")
    log.info("┗" + "━"*78 + "┛")
    log.info(f"   Model: {LLAMA_MODEL_PATH}")
    log.info(f"   Context: {LLAMA_CTX}, Threads: {LLAMA_THREADS}")
    try:
        llama = ChatLlamaCpp(
            model_path=LLAMA_MODEL_PATH,
            n_ctx=LLAMA_CTX,
            n_threads=LLAMA_THREADS,
            temperature=0.0,
            max_tokens=LLAMA_MAX_TOKENS,
            verbose=False,
        )
        log.info("✅ Llama model loaded successfully\n")
    except Exception as e:
        log.error(f"❌ Failed to load Llama model: {e}")
        return {"ok": False, "error": str(e)}

    # 모드 자동 판단
    log.info("┏" + "━"*78 + "┓")
    log.info("┃ 🎯 MODE DETECTION")
    log.info("┗" + "━"*78 + "┛")
    mode = _detect_mode(file_paths, texts, llama)
    state["mode"] = mode
    log.info(f"   Selected Mode: {mode.upper()}")
    log.info(f"   Files: {file_paths or []}")
    log.info(f"   Texts: {texts or []}\n")

    user_hint = {"file_paths": file_paths or [], "texts": texts or [], "mode": mode}
    history: List[HumanMessage] = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Inputs: {json.dumps(user_hint, ensure_ascii=False)}")
    ]

    for step in range(1, max_steps + 1):
        log.info(f"\n{'━'*80}")
        log.info(f"🔄 STEP {step}/{max_steps}")
        log.info(f"{'━'*80}")

        ai = llama.invoke(history)
        text = getattr(ai, "content", "")

        # Thought 추출 및 출력
        thought_match = re.search(r"Thought:\s*(.+?)(?:\n|Action:|$)", text, flags=re.S)
        if thought_match:
            thought = thought_match.group(1).strip()
            log.info(f"💭 THOUGHT: {thought}")

        # Action 추출 및 출력
        action_match = re.search(r"Action:\s*(.*?)(?:\n\n|Observation:|$)", text, flags=re.S)
        if action_match:
            action = action_match.group(1).strip()
            log.info(f"⚡ ACTION:\n{action}")

        # FinalAnswer 체크
        m_final = re.search(r"FinalAnswer:\s*(.+)", text, flags=re.S)
        if m_final and not _extract_tool_call(text):
            final_msg = m_final.group(1).strip()
            state["final_message"] = final_msg
            log.info(f"\n{'🎯'*40}")
            log.info(f"✅ FINAL ANSWER: {final_msg}")
            log.info(f"{'🎯'*40}\n")
            break

        # 도구 호출 추출
        call = _extract_tool_call(text)
        if not call:
            # 힌트를 강제로 실행 (LLM이 판단하지 않고 바로 실행)
            mode = state.get("mode", "generate")

            log.warning(f"⚠️  No tool call extracted, providing forced hint (step {step}, mode {mode})")

            # 검증 모드 강제 순서
            if mode == "validate":
                if step == 1:
                    # 첫 단계: 무조건 파싱
                    call = {
                        "tool": "parse_documents",
                        "args": {"file_paths": file_paths}
                    }
                    log.info(f"🔧 FORCED TOOL (step {step}): parse_documents")
                elif step == 2:
                    # 두 번째 단계: 무조건 검증 리포트
                    call = {
                        "tool": "generate_validation_report",
                        "args": {"output_format": "markdown", "output_dir": "output"}
                    }
                    log.info(f"🔧 FORCED TOOL (step {step}): generate_validation_report")
                else:
                    # 3단계 이상이면 종료
                    log.info(f"🔧 FORCED COMPLETION: All validation steps done (step {step})")
                    state["final_message"] = state.get("report_path", "Validation completed")
                    break

            # 생성 모드 강제 순서
            else:
                if step == 1 and file_paths:
                    # Excel/CSV 파일 찾기
                    excel_file = next((f for f in file_paths if f.endswith(('.xlsx', '.xls', '.csv'))), None)
                    if excel_file:
                        call = {
                            "tool": "generate_all_modules",
                            "args": {"excel_path": excel_file, "output_dir": "output"}
                        }
                        log.info(f"🔧 FORCED TOOL (step {step}): generate_all_modules")
                    else:
                        # Excel/CSV가 없으면 종료
                        log.error(f"❌ No Excel/CSV file found for generation mode")
                        state["final_message"] = "Error: No Excel/CSV file found"
                        break
                elif step == 2:
                    call = {"tool": "save_as_pdf", "args": {"output_dir": "output"}}
                    log.info(f"🔧 FORCED TOOL (step {step}): save_as_pdf")
                else:
                    # 3단계 이상이면 종료
                    log.info(f"🔧 FORCED COMPLETION: All generation steps done (step {step})")
                    state["final_message"] = state.get("pdf_path", "Generation completed")
                    break

            # LLM에게도 알림
            if call:
                history.append(HumanMessage(content=f"System: Executing forced action: {json.dumps(call, ensure_ascii=False)}"))
            # continue 대신 call을 직접 실행하도록 아래로 진행

        tool_name = call.get("tool")
        args = call.get("args") or {}
        tool_obj = TOOLS.get(tool_name)

        if not tool_obj:
            log.warning(f"⚠️  INVALID TOOL: '{tool_name}' - Available: {list(TOOLS.keys())}")
            history.append(HumanMessage(
                content=f"Observation: invalid tool '{tool_name}'. Available: {list(TOOLS.keys())}"
            ))
            continue

        # 도구 실행
        log.info(f"🔧 EXECUTING TOOL: '{tool_name}'")
        log.info(f"   Args: {json.dumps(args, ensure_ascii=False, indent=2)}")
        try:
            result = _run_tool(tool_obj, args, state)
            log.info(f"✅ TOOL SUCCESS: '{tool_name}' - Result: {result.get('ok', True)}")
            # 결과 요약 출력
            if isinstance(result, dict):
                if 'error' not in result:
                    log.info(f"   📊 Result summary: {str(result)[:200]}...")
        except Exception as e:
            result = {"ok": False, "error": str(e)}
            log.error(f"❌ TOOL FAILED: '{tool_name}' - Error: {e}")

        # 파싱 결과를 state에 저장 (검증에 활용)
        if tool_name == "parse_documents" and isinstance(result, dict) and result.get("ok"):
            parsed_text = ""
            for file_result in result.get("results", []):
                # Upstage 파싱 결과에서 텍스트 추출
                if "text" in file_result:
                    parsed_text += file_result["text"] + "\n\n"
                elif "content" in file_result:
                    parsed_text += file_result["content"] + "\n\n"

            state["parsed_content"] = parsed_text
            log.info(f"   📄 Parsed content saved to state ({len(parsed_text)} chars)")

        # Observation 생성 및 로깅
        observation = f"Observation: {json.dumps(result, ensure_ascii=False)[:2000]}"
        log.info(f"📝 OBSERVATION: {observation[:500]}...")
        history.append(HumanMessage(content=observation))

        # 모드별 완료 처리
        mode = state.get("mode", "generate")

        if mode == "generate":
            # 생성 모드: PDF 저장 완료시 종료
            if tool_name == "save_as_pdf" and isinstance(result, dict) and result.get("ok"):
                state["pdf_path"] = result.get("path")
                state["pdf_size"] = result.get("size", 0)

                # Module 2 PDF 정보도 저장
                if result.get("module2_path"):
                    state["module2_pdf_path"] = result.get("module2_path")
                    state["module2_pdf_size"] = result.get("module2_size", 0)

                log.info(f"\n{'🎉'*40}")
                log.info(f"✅ CTD GENERATION COMPLETED")
                log.info(f"📄 Complete PDF: {result.get('path')} ({result.get('size', 0):,} bytes)")
                if result.get("module2_path"):
                    log.info(f"📄 Module 2 PDF: {result.get('module2_path')} ({result.get('module2_size', 0):,} bytes)")
                log.info(f"{'🎉'*40}\n")

                final_msg = f"PDF saved -> Complete: {result.get('path')}"
                if result.get("module2_path"):
                    final_msg += f" | Module2: {result.get('module2_path')}"
                history.append(HumanMessage(content=f"FinalAnswer: {final_msg}"))
                break

            # 모든 모듈 생성 완료시 PDF 저장 힌트
            if tool_name == "generate_all_modules" and isinstance(result, dict) and result.get("ok"):
                state["modules_generated"] = result.get("modules", [])
                log.info(f"📝 Modules generated: {len(result.get('modules', []))} modules")

        else:  # validate 모드
            # 검증 모드: 리포트 생성 완료시 종료
            if tool_name == "generate_validation_report" and isinstance(result, dict) and result.get("ok"):
                state["report_path"] = result.get("report_path")
                state["summary"] = result.get("summary", {})

                # 스키마 체크 정보 저장 (웹 UI에 전달용)
                if "schema_check" in result:
                    state["schema_check"] = result["schema_check"]

                summary_text = f"검증 완료: 통과 {result.get('summary', {}).get('passed', 0)}, 실패 {result.get('summary', {}).get('failed', 0)}, 경고 {result.get('summary', {}).get('warnings', 0)}"
                log.info(f"\n{'🎉'*40}")
                log.info(f"✅ VALIDATION COMPLETED")
                log.info(f"📊 Summary: {summary_text}")
                log.info(f"📄 Report: {result.get('report_path')}")
                if "schema_check" in result:
                    schema_check = result["schema_check"]
                    log.info(f"📋 ICH Schema: {schema_check.get('found', 0)}/{schema_check.get('total_required', 0)} items found")
                log.info(f"{'🎉'*40}\n")
                history.append(HumanMessage(content=f"FinalAnswer: {summary_text} | Report -> {result.get('report_path')}"))
                break

    return state


if __name__ == "__main__":
    # 간단한 테스트
    result = run_agent(texts=["당뇨병 고혈압 치료"])
    print("\n" + "="*70)
    print("Agent Result:", result.get("final_message", "No final message"))
    print("="*70)
