const API_URL = "http://localhost:8000";

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    
    const form = document.getElementById("review-form");
    form.addEventListener("submit", handleFormSubmit);

    const codeInput = document.getElementById("code-input");
    const fileInput = document.getElementById("file-input");
    const fileName = document.getElementById("file-name");

    codeInput.addEventListener("input", () => {
        updateInputStats();
        if (codeInput.value.trim() !== "") {
            fileInput.value = "";
            fileName.textContent = "No file selected";
        }
    });

    fileInput.addEventListener("change", () => {
        const selectedFile = fileInput.files[0];
        if (selectedFile) {
            codeInput.value = "";
            fileName.textContent = `${selectedFile.name} (${formatBytes(selectedFile.size)})`;
        } else {
            fileName.textContent = "No file selected";
        }
        updateInputStats();
    });

    updateInputStats();
});

async function checkHealth() {
    const badge = document.getElementById("health-badge");
    try {
        const res = await fetch(`${API_URL}/health`);
        const data = await res.json();
        
        if (data.status === "ok") {
            badge.textContent = "Ollama: Connected";
            badge.className = "badge ok";
        } else {
            badge.textContent = "Ollama: Unreachable";
            badge.className = "badge error";
        }
    } catch (err) {
        console.error("Health check error:", err);
        badge.textContent = "Ollama: Unreachable";
        badge.className = "badge error";
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const code = document.getElementById("code-input").value;
    const file = document.getElementById("file-input").files[0];
    const mode = document.getElementById("mode-select").value;
    const question = document.getElementById("question-input").value;

    const loader = document.getElementById("loader");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    const resultSection = document.getElementById("result-section");
    const submitBtn = document.getElementById("submit-btn");
    const formHint = document.getElementById("form-hint");

    if (!code.trim() && !file) {
        formHint.textContent = "Paste code or upload a supported file before running an audit.";
        formHint.className = "form-hint error";
        return;
    }

    formHint.textContent = "";
    formHint.className = "form-hint";
    errorCard.classList.add("hidden");
    resultSection.classList.add("hidden");
    loader.classList.remove("hidden");
    submitBtn.disabled = true;
    submitBtn.textContent = "Analyzing Code...";

    const formData = new FormData();
    if (file) {
        formData.append("file", file);
    } else {
        formData.append("code", code);
    }
    
    if (mode && mode !== "auto") {
        formData.append("mode", mode);
    }
    if (question.trim()) {
        formData.append("question", question);
    }

    try {
        const response = await fetch(`${API_URL}/review`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "An error occurred during code analysis.");
        }

        renderResults(data);
        resultSection.classList.remove("hidden");
    } catch (err) {
        console.error("Review request failed:", err);
        errorMessage.textContent = err.message || "Failed to connect to review server.";
        errorCard.classList.remove("hidden");
    } finally {
        loader.classList.add("hidden");
        submitBtn.disabled = false;
        submitBtn.textContent = "Run Audit";
        checkHealth();
    }
}

function renderResults(result) {
    const riskBadge = document.getElementById("risk-badge");
    const submissionType = document.getElementById("res-submission-type");
    const summaryText = document.getElementById("res-summary-text");
    const findingCount = document.getElementById("res-finding-count");
    const topSeverity = document.getElementById("res-top-severity");

    riskBadge.textContent = `${result.overall_risk_level} Risk`;
    riskBadge.className = `badge risk-${result.overall_risk_level}`;
    
    submissionType.textContent = titleCase(result.submission_type.replace("_", " "));
    findingCount.textContent = result.findings ? result.findings.length : 0;
    topSeverity.textContent = getTopSeverity(result.findings);
    summaryText.textContent = result.summary;

    const findingsList = document.getElementById("findings-list");
    const noFindingsCard = document.getElementById("no-findings-card");
    
    findingsList.innerHTML = "";
    
    if (!result.findings || result.findings.length === 0) {
        noFindingsCard.classList.remove("hidden");
        return;
    } else {
        noFindingsCard.classList.add("hidden");
    }

    const grouped = {
        security: [],
        bug: [],
        architecture: [],
        clean_code: [],
        performance: []
    };

    result.findings.forEach(f => {
        if (grouped[f.category]) {
            grouped[f.category].push(f);
        } else {
            grouped[f.category] = [f];
        }
    });

    const categoryHeaders = {
        security: "Security Findings",
        bug: "Logic & Bug Findings",
        architecture: "Architecture Findings",
        clean_code: "Clean Code Findings",
        performance: "Performance Findings"
    };

    Object.keys(grouped).forEach(cat => {
        const findings = grouped[cat];
        if (findings.length === 0) return;

        const block = document.createElement("div");
        block.className = "category-block";

        const title = document.createElement("h3");
        title.className = "category-title";
        title.textContent = categoryHeaders[cat] || cat.toUpperCase();
        block.appendChild(title);

        findings.forEach(f => {
            const card = document.createElement("div");
            card.className = `finding-card ${f.severity}`;

            let linesStr = "N/A";
            if (f.line_start !== null && f.line_start !== undefined) {
                if (f.line_end !== null && f.line_end !== undefined && f.line_end !== f.line_start) {
                    linesStr = `Lines ${f.line_start}-${f.line_end}`;
                } else {
                    linesStr = `Line ${f.line_start}`;
                }
            }

            card.innerHTML = `
                <div class="finding-header">
                    <div class="finding-meta">
                        <span class="finding-severity ${f.severity}">${f.severity.toUpperCase()}</span>
                        <span class="finding-lines">${linesStr}</span>
                    </div>
                    <span class="finding-confidence">Confidence: ${Math.round(f.confidence * 100)}%</span>
                </div>
                <p class="finding-desc">${escapeHTML(f.description)}</p>
                <div class="finding-suggestion">
                    <strong>Suggestion / Fix:</strong>
                    <p>${escapeHTML(f.suggestion)}</p>
                </div>
            `;
            block.appendChild(card);
        });

        findingsList.appendChild(block);
    });
}

function updateInputStats() {
    const codeInput = document.getElementById("code-input");
    const fileInput = document.getElementById("file-input");
    const inputStats = document.getElementById("input-stats");
    const code = codeInput.value;
    const file = fileInput.files[0];

    if (file) {
        inputStats.textContent = formatBytes(file.size);
        return;
    }

    if (!code.trim()) {
        inputStats.textContent = "0 lines";
        return;
    }

    const lines = code.split(/\r\n|\r|\n/).length;
    inputStats.textContent = `${lines} ${lines === 1 ? "line" : "lines"} / ${formatBytes(new Blob([code]).size)}`;
}

function getTopSeverity(findings = []) {
    if (!findings || findings.length === 0) return "None";

    const severityRank = {
        info: 1,
        low: 2,
        medium: 3,
        high: 4,
        critical: 5
    };

    const top = findings.reduce((current, finding) => {
        const currentRank = severityRank[current] || 0;
        const nextRank = severityRank[finding.severity] || 0;
        return nextRank > currentRank ? finding.severity : current;
    }, "info");

    return titleCase(top);
}

function titleCase(value) {
    return value
        .split(" ")
        .filter(Boolean)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

function formatBytes(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / Math.pow(1024, index);
    return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function escapeHTML(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
