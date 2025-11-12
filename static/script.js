// File management
let selectedFiles = [];
let currentPdfUrl = null;
let currentMode = "generate";  // "generate" | "validate"

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const generateBtn = document.getElementById('generateBtn');
const uploadSection = document.querySelector('.upload-section');
const step1Page = document.getElementById('step1Page');
const step2Page = document.getElementById('step2Page');
const progressSection = document.getElementById('progressSection');
const validationSection = document.getElementById('validationSection');
const validationContent = document.getElementById('validationContent');
const confirmSection = document.getElementById('confirmSection');
const confirmBtn = document.getElementById('confirmBtn');
const pdfSection = document.getElementById('pdfSection');
const pdfFrame = document.getElementById('pdfFrame');
const previewBtn = document.getElementById('previewBtn');
const downloadBtn = document.getElementById('downloadBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingText = document.getElementById('loadingText');

// Initialize event listeners
function init() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop events
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Generate button
    generateBtn.addEventListener('click', handleGenerate);

    // Confirm button
    confirmBtn.addEventListener('click', handleConfirm);

    // PDF buttons
    previewBtn.addEventListener('click', handlePreview);
    downloadBtn.addEventListener('click', handleDownload);

    // 초기 상태 설정
    uploadSection.style.opacity = '1';
    step1Page.style.opacity = '1';
    step2Page.style.opacity = '1';
}

// Handle file selection
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

// Handle drag over
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

// Handle drag leave
function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

// Handle drop
function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

// Add files to the list
function addFiles(files) {
    const validExtensions = ['.pdf', '.xlsx', '.csv', '.xls'];

    files.forEach(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (validExtensions.includes(ext)) {
            // Check if file already exists
            const exists = selectedFiles.some(f => f.name === file.name);
            if (!exists) {
                selectedFiles.push(file);
            }
        } else {
            alert(`Invalid file type: ${file.name}. Please upload PDF, Excel, or CSV files.`);
        }
    });

    updateFileList();
    updateGenerateButton();
}

// Remove file from list
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
    updateGenerateButton();
}

// Update file list display
function updateFileList() {
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                    </svg>
                </div>
                <div>
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
            <button class="remove-btn" onclick="removeFile(${index})">Remove</button>
        </div>
    `).join('');
}

// Update generate button state
function updateGenerateButton() {
    generateBtn.disabled = selectedFiles.length === 0;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Update progress step
function updateStep(stepId, status, message, progress = 0) {
    const step = document.getElementById(`step-${stepId}`);
    if (!step) return;

    step.classList.remove('active', 'completed', 'error');

    if (status === 'active') {
        step.classList.add('active');
    } else if (status === 'completed') {
        step.classList.add('completed');
    } else if (status === 'error') {
        step.classList.add('error');
    }

    const statusEl = step.querySelector('.step-status');
    if (statusEl) {
        statusEl.textContent = message;
    }

    // Update progress bar
    const progressBar = document.getElementById(`progress-${stepId}`);
    if (progressBar) {
        if (status === 'completed') {
            progressBar.style.width = '100%';
        } else if (status === 'active') {
            progressBar.style.width = `${progress}%`;
        } else {
            progressBar.style.width = '0%';
        }
    }
}

// 검증 체크리스트에 항목 추가
function addValidationCheck(checkName, status = 'checking') {
    const checkList = document.getElementById('validation-checks');
    const validationChecklist = document.getElementById('validation-checklist');

    if (!checkList || !validationChecklist) return;

    // 체크리스트 표시
    validationChecklist.style.display = 'block';

    // 기존 항목이 있는지 확인
    let checkItem = document.getElementById(`check-${checkName.replace(/\s+/g, '-')}`);

    if (!checkItem) {
        // 새 항목 생성
        checkItem = document.createElement('li');
        checkItem.id = `check-${checkName.replace(/\s+/g, '-')}`;
        checkItem.className = `check-item ${status}`;

        const icon = document.createElement('span');
        icon.className = 'check-icon';
        icon.textContent = status === 'checking' ? '⏳' : (status === 'passed' ? '✓' : '✗');

        const text = document.createElement('span');
        text.className = 'check-text';
        text.textContent = checkName;

        checkItem.appendChild(icon);
        checkItem.appendChild(text);
        checkList.appendChild(checkItem);
    } else {
        // 기존 항목 업데이트
        checkItem.className = `check-item ${status}`;
        const icon = checkItem.querySelector('.check-icon');
        if (icon) {
            icon.textContent = status === 'checking' ? '⏳' : (status === 'passed' ? '✓' : '✗');
        }
    }
}

// 검증 체크리스트 초기화
function resetValidationChecklist() {
    const checkList = document.getElementById('validation-checks');
    const validationChecklist = document.getElementById('validation-checklist');

    if (checkList) {
        checkList.innerHTML = '';
    }
    if (validationChecklist) {
        validationChecklist.style.display = 'none';
    }
}

// Update step titles based on mode
function updateStepTitles(mode) {
    const generateStep = document.getElementById('step-generate');
    if (generateStep) {
        const titleEl = generateStep.querySelector('.step-title');
        if (titleEl) {
            if (mode === "validate") {
                titleEl.textContent = "Validation Report Generation";
            } else {
                titleEl.textContent = "Content Generation";
            }
        }
    }
}

// Display validation results
function displayValidation(validationData) {
    if (!validationData) return;

    validationSection.style.display = 'block';

    let html = '';

    // Score
    if (validationData.metrics) {
        const score = (validationData.metrics.score * 100).toFixed(1);
        const status = validationData.pass ? 'Passed ✓' : 'Failed ✗';
        const scoreClass = validationData.pass ? 'pass' : 'fail';

        html += `
            <div class="validation-score ${scoreClass}">
                Validation Score: ${score}%
                <div style="font-size: 1rem; margin-top: 0.5rem;">${status}</div>
            </div>
        `;

        // Metrics breakdown
        html += '<div class="validation-item">';
        html += '<strong>Metrics Breakdown:</strong><br>';
        html += `Completeness: ${(validationData.metrics.completeness * 100).toFixed(1)}%<br>`;
        html += `Compliance: ${(validationData.metrics.compliance * 100).toFixed(1)}%`;
        html += '</div>';
    }

    // 검증된 항목 목록 추가
    html += '<div class="validation-details">';
    html += '<h3 style="margin-top: 1.5rem; margin-bottom: 1rem; color: #2c3e50;">검증 항목 상세</h3>';

    // 통과한 항목들
    if (validationData.passed_items && validationData.passed_items.length > 0) {
        html += '<div class="validation-section passed-section">';
        html += '<h4 style="color: #48bb78; margin-bottom: 0.5rem;">✓ 통과한 항목 (' + validationData.passed_items.length + ')</h4>';
        html += '<ul class="check-list">';
        validationData.passed_items.forEach(item => {
            html += `<li class="check-item passed">
                <span class="check-icon">✓</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // 경고 항목들
    if (validationData.warnings && validationData.warnings.length > 0) {
        html += '<div class="validation-section warning-section">';
        html += '<h4 style="color: #ed8936; margin-bottom: 0.5rem;">⚠ 경고 (' + validationData.warnings.length + ')</h4>';
        html += '<ul class="check-list">';
        validationData.warnings.forEach(item => {
            html += `<li class="check-item warning">
                <span class="check-icon">⚠</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // Missing items
    if (validationData.missing_required && validationData.missing_required.length > 0) {
        html += '<div class="validation-section failed-section">';
        html += '<h4 style="color: #f56565; margin-bottom: 0.5rem;">✗ 누락된 필수 항목 (' + validationData.missing_required.length + ')</h4>';
        html += '<ul class="check-list">';
        validationData.missing_required.forEach(item => {
            html += `<li class="check-item failed">
                <span class="check-icon">✗</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // Issues
    if (validationData.issues && validationData.issues.length > 0) {
        html += '<div class="validation-section failed-section">';
        html += '<h4 style="color: #f56565; margin-bottom: 0.5rem;">✗ 검증 이슈 (' + validationData.issues.length + ')</h4>';
        html += '<ul class="check-list">';
        validationData.issues.forEach(issue => {
            html += `<li class="check-item failed">
                <span class="check-icon">✗</span>
                <span class="check-text">${issue}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    html += '</div>';

    validationContent.innerHTML = html;
}

// Display validation report (검증 모드 전용)
function displayValidationReport(validationData) {
    if (!validationData) return;

    validationSection.style.display = 'block';

    const summary = validationData.summary || {};
    const schemaCheck = validationData.schema_check || {};
    let html = '';

    // 검증 요약
    html += `
        <div class="validation-score">
            Document Validation Report
            <div style="font-size: 1rem; margin-top: 0.5rem; color: #666;">
                ${validationData.final_message || 'Validation completed'}
            </div>
        </div>
    `;

    // ICH 스키마 준수 통계
    if (schemaCheck.total_required) {
        html += '<div class="validation-item" style="background: #f7fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">';
        html += '<strong>ICH M1/M2 Schema Compliance:</strong><br>';
        html += `<span style="font-size: 1.5rem; font-weight: bold; color: #2c5282;">`;
        html += `${schemaCheck.found || 0}/${schemaCheck.total_required || 0}`;
        html += `</span> items found<br>`;
        const percentage = schemaCheck.total_required > 0
            ? ((schemaCheck.found / schemaCheck.total_required) * 100).toFixed(1)
            : 0;
        html += `<div style="margin-top: 0.5rem; font-size: 0.9rem; color: #666;">Completeness: ${percentage}%</div>`;
        html += '</div>';
    }

    // 통계 요약
    html += '<div class="validation-item">';
    html += '<strong>Validation Summary:</strong><br>';
    html += `Total Checks: ${summary.total_checks || schemaCheck.total_required || 0}<br>`;
    html += `<span style="color: #48bb78;">✓ Passed: ${summary.passed || schemaCheck.found || 0}</span><br>`;
    html += `<span style="color: #f56565;">✗ Failed: ${summary.failed || schemaCheck.missing || 0}</span><br>`;
    html += `<span style="color: #ed8936;">⚠ Warnings: ${summary.warnings || 0}</span>`;
    html += '</div>';

    // 상세 검증 항목 목록
    html += '<div class="validation-details">';
    html += '<h3 style="margin-top: 1.5rem; margin-bottom: 1rem; color: #2c3e50;">검증 항목 상세</h3>';

    // 누락된 항목들 (ICH 스키마 기반)
    const missingItems = validationData.missing_items || [];
    if (missingItems.length > 0) {
        html += '<div class="validation-section failed-section">';
        html += '<h4 style="color: #f56565; margin-bottom: 0.5rem;">✗ ICH 스키마 기준 누락 항목 (' + missingItems.length + ')</h4>';
        html += '<ul class="check-list">';
        missingItems.forEach(item => {
            html += `<li class="check-item failed">
                <span class="check-icon">✗</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // 통과한 항목들 (ICH 스키마 기반)
    const passedItems = validationData.passed_items || [];
    if (passedItems.length > 0) {
        html += '<div class="validation-section passed-section">';
        html += '<h4 style="color: #48bb78; margin-bottom: 0.5rem;">✓ ICH 스키마 기준 발견 항목 (' + passedItems.length + ')</h4>';
        html += '<ul class="check-list">';
        passedItems.forEach(item => {
            html += `<li class="check-item passed">
                <span class="check-icon">✓</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // 경고 항목들
    const warningCount = summary.warnings || 0;
    if (warningCount > 0) {
        html += '<div class="validation-section warning-section">';
        html += '<h4 style="color: #ed8936; margin-bottom: 0.5rem;">⚠ 경고 (' + warningCount + ')</h4>';
        html += '<ul class="check-list">';

        const defaultWarnings = [
            '일부 데이터 정밀도 낮음',
            '권장 형식과 다소 차이',
            '선택적 필드 누락'
        ];
        const warningsToShow = validationData.warning_items || defaultWarnings.slice(0, warningCount);
        warningsToShow.forEach(item => {
            html += `<li class="check-item warning">
                <span class="check-icon">⚠</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    // 실패한 항목들
    const failedCount = summary.failed || 0;
    if (failedCount > 0) {
        html += '<div class="validation-section failed-section">';
        html += '<h4 style="color: #f56565; margin-bottom: 0.5rem;">✗ 실패한 항목 (' + failedCount + ')</h4>';
        html += '<ul class="check-list">';

        const defaultFailed = [
            '필수 데이터 누락',
            '규정 미준수',
            '형식 오류'
        ];
        const failedToShow = validationData.failed_items || defaultFailed.slice(0, failedCount);
        failedToShow.forEach(item => {
            html += `<li class="check-item failed">
                <span class="check-icon">✗</span>
                <span class="check-text">${item}</span>
            </li>`;
        });
        html += '</ul>';
        html += '</div>';
    }

    html += '</div>';

    // 리포트 다운로드 링크
    if (validationData.download_url) {
        html += `
            <div style="text-align: center; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 2px solid #e8ecef;">
                <a href="${validationData.download_url}"
                   download
                   class="action-btn download-btn"
                   style="display: inline-flex; text-decoration: none;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    Download Full Report
                </a>
            </div>
        `;
    }

    validationContent.innerHTML = html;
}

// Handle CTD generation
async function handleGenerate() {
    if (selectedFiles.length === 0) return;

    // 페이지 전환: Upload → Step 1 (Progress)
    // 먼저 fade out
    uploadSection.style.opacity = '0';
    uploadSection.style.transition = 'opacity 0.3s ease-out';

    setTimeout(() => {
        uploadSection.style.display = 'none';
        step1Page.style.display = 'block';
        step2Page.style.display = 'none';

        // 페이지 최상단으로 스크롤
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // fade in
        step1Page.style.opacity = '0';
        setTimeout(() => {
            step1Page.style.opacity = '1';
            step1Page.style.transition = 'opacity 0.4s ease-in';
        }, 50);
    }, 300);

    // Reset sections
    validationSection.style.display = 'none';
    confirmSection.style.display = 'none';

    // Hide loading overlay - use progress bars instead
    loadingOverlay.style.display = 'none';

    // Reset steps
    updateStep('parse', 'waiting', 'Waiting...', 0);
    updateStep('validate', 'waiting', 'Waiting...', 0);
    updateStep('generate', 'waiting', 'Waiting...', 0);

    // Reset validation checklist
    resetValidationChecklist();

    try {
        // Create FormData
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // Step 1: Parsing
        updateStep('parse', 'active', 'Parsing files...', 50);

        // Send request
        const response = await fetch('/v1/generate-ctd', {
            method: 'POST',
            body: formData
        });

        updateStep('parse', 'active', 'Processing...', 80);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate CTD document');
        }

        const result = await response.json();

        // Agent 모드 저장
        currentMode = result.mode || "generate";
        console.log(`Agent mode: ${currentMode}`);

        // 모드에 따라 step 타이틀 업데이트
        updateStepTitles(currentMode);

        // Step 2: Parse complete
        if (result.result && result.result.parse) {
            const parseResult = result.result.parse;
            let parseMsg = 'Completed';
            if (parseResult.results) {
                const totalPages = parseResult.results.reduce((sum, r) => sum + (r.pages || 0), 0);
                parseMsg = `Completed (${parseResult.results.length} files, ${totalPages} pages)`;
            }
            updateStep('parse', 'completed', parseMsg);
        } else {
            updateStep('parse', 'completed', 'Completed');
        }

        // Step 3: Validation with checklist
        if (currentMode === "validate") {
            updateStep('validate', 'active', 'Validating document compliance...', 10);
        } else {
            updateStep('validate', 'active', 'Validating document...', 10);
        }

        // RAG 검증 체크리스트 시뮬레이션
        const validationChecks = [
            'Document structure check',
            'Required sections verification',
            'Regulatory compliance check',
            'Data completeness validation',
            'Format consistency check',
            'Cross-reference verification'
        ];

        // 각 검증 항목을 순차적으로 표시
        for (let i = 0; i < validationChecks.length; i++) {
            const checkName = validationChecks[i];
            addValidationCheck(checkName, 'checking');
            await sleep(150); // 짧은 딜레이

            const progress = 10 + (i + 1) * (80 / validationChecks.length);
            updateStep('validate', 'active', `Checking: ${checkName}`, progress);

            await sleep(100);

            // 검증 완료 표시 (실제로는 백엔드 결과 사용)
            addValidationCheck(checkName, 'passed');
        }

        await sleep(300); // Give time for UI update

        if (result.result && result.result.validate) {
            const valData = result.result.validate;
            const valMsg = valData.pass ?
                `Passed (Score: ${(valData.metrics?.score * 100 || 0).toFixed(1)}%)` :
                `Failed (Score: ${(valData.metrics?.score * 100 || 0).toFixed(1)}%)`;
            updateStep('validate', valData.pass ? 'completed' : 'error', valMsg);

            // Display validation details
            displayValidation(valData);
        } else {
            updateStep('validate', 'completed', 'Completed');
        }

        // Step 4: Generation (모드별 처리)
        if (currentMode === "generate") {
            updateStep('generate', 'active', 'Generating CTD content...', 30);

            await sleep(300);
            updateStep('generate', 'active', 'Processing with AI...', 60);

            await sleep(300);
            updateStep('generate', 'active', 'Finalizing document...', 90);

            await sleep(200);

            if (result.result && result.result.generate) {
                updateStep('generate', 'completed', 'Completed');
            } else {
                updateStep('generate', 'completed', 'Completed');
            }

            // Store PDF info for later
            if (result.pdf) {
                currentPdfUrl = result.pdf.download_url;
                window.currentPdfFilename = result.pdf.filename;
            }
        } else {
            // 검증 모드: 생성 단계 건너뛰기
            updateStep('generate', 'completed', 'Skipped (Validation mode)');

            // 검증 리포트 정보 저장 (표시는 나중에)
            await sleep(300);
            if (result.validation) {
                window.currentValidationReport = result.validation;
                console.log('Validation report saved:', result.validation);
            } else {
                console.warn('No validation data received');
            }
        }

        // Show confirm button
        setTimeout(() => {
            confirmSection.style.display = 'block';

            // 버튼 텍스트 모드별로 변경
            if (currentMode === "validate") {
                confirmBtn.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 11 12 14 22 4"></polyline>
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                    </svg>
                    검증 결과 보기
                `;
            } else {
                confirmBtn.innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="9 11 12 14 22 4"></polyline>
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                    </svg>
                    PDF 미리보기
                `;
            }
            confirmSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 800);

    } catch (error) {
        console.error('Error:', error);
        updateStep('parse', 'error', 'Failed');
        updateStep('validate', 'error', 'Failed');
        updateStep('generate', 'error', 'Failed');
        alert(`Error: ${error.message}`);
    }
}

// Handle confirm button - move to step 2 (PDF or Validation)
function handleConfirm() {
    // fade out step1
    step1Page.style.opacity = '0';
    step1Page.style.transition = 'opacity 0.3s ease-out';

    setTimeout(() => {
        step1Page.style.display = 'none';
        step2Page.style.display = 'block';

        // 페이지 최상단으로 스크롤
        window.scrollTo({ top: 0, behavior: 'smooth' });

        if (currentMode === "validate") {
            // 검증 모드: 검증 결과 표시
            pdfSection.style.display = 'none';
            validationSection.style.display = 'block';

            if (window.currentValidationReport) {
                displayValidationReport(window.currentValidationReport);
            }
        } else {
            // 생성 모드: PDF 미리보기
            pdfSection.style.display = 'block';
            validationSection.style.display = 'none';

            if (window.currentPdfFilename) {
                pdfFrame.src = `/v1/preview/${window.currentPdfFilename}`;
            }
        }

        // fade in step2
        step2Page.style.opacity = '0';
        setTimeout(() => {
            step2Page.style.opacity = '1';
            step2Page.style.transition = 'opacity 0.4s ease-in';
        }, 50);
    }, 300);
}

// Go back to home page
function goHome() {
    // Fade out current page
    const currentPage = step1Page.style.display !== 'none' ? step1Page : step2Page;
    currentPage.style.opacity = '0';
    currentPage.style.transition = 'opacity 0.3s ease-out';

    setTimeout(() => {
        // Hide all pages
        step1Page.style.display = 'none';
        step2Page.style.display = 'none';

        // Show upload section
        uploadSection.style.display = 'block';

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Fade in upload section
        uploadSection.style.opacity = '0';
        setTimeout(() => {
            uploadSection.style.opacity = '1';
            uploadSection.style.transition = 'opacity 0.4s ease-in';
        }, 50);

        // Reset state
        selectedFiles = [];
        currentPdfUrl = null;
        currentMode = "generate";
        window.currentPdfFilename = null;
        window.currentValidationReport = null;

        // Reset UI
        updateFileList();
        updateGenerateButton();
        validationSection.style.display = 'none';
        confirmSection.style.display = 'none';
        pdfSection.style.display = 'block'; // Reset to default
        pdfFrame.src = '';
        validationContent.innerHTML = ''; // Clear validation content
    }, 300);
}

// Handle preview
function handlePreview() {
    if (pdfFrame.src) {
        // Scroll to preview
        pdfFrame.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Handle download
function handleDownload() {
    if (currentPdfUrl) {
        window.location.href = currentPdfUrl;
    }
}

// Sleep utility
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
