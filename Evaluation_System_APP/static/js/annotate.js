// Canvas and UI elements
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const img = new Image();
const scopeInput = document.getElementById('scopeInput');
const bidInput = document.getElementById('bidInput');
const reasonInput = document.getElementById('reasonInput');
const previousTags = document.getElementById('previousTags');
const debugInfo = document.getElementById('debugInfo');

// State variables
let selected = new Set();
let historyStack = [];
let pendingTag = null;
let lastScrollY = 0;
let debugMode = false;

// Initialize canvas when image loads
img.onload = () => { 
    canvas.width = img.width; 
    canvas.height = img.height; 
    redraw(); 
    updatePreviousTagsDisplay();
};
img.src = IMAGE_URL;

// Debug info
function updateDebugInfo(x, y) {
    if (!debugMode) return;
    debugInfo.innerHTML = `
        Mouse: (${x}, ${y})<br>
        Regions: ${REGIONS.length}<br>
        Selected: ${selected.size}<br>
        ${Array.from(selected).map(id => {
            const r = REGIONS.find(rr => rr.id === id);
            return `Region ${id}: ${JSON.stringify(r.pts)}`;
        }).join('<br>')}
    `;
}

// Update previous tags display
function updatePreviousTagsDisplay() {
    previousTags.innerHTML = '';
    REGIONS.filter(r => r.tag).forEach(r => {
        const div = document.createElement('div');
        div.className = 'tag-item' + (r.auto_tagged ? ' auto-tagged' : '');
        const tagText = typeof r.tag === 'string' ? r.tag : r.tag.value;
        div.innerHTML = `
            <div>
                <span class="tag-scope">${tagText}</span>
                <span class="tag-bid">Bid Item: ${r.bidItem}</span>
                ${r.auto_tagged ? '<span class="auto-tag-badge">Auto-tagged</span>' : ''}
                <div class="tag-text">Text: "${r.text || 'N/A'}"</div>
                ${r.reason ? `<div class="tag-reason">Reason: ${r.reason}</div>` : ''}
            </div>
            <div>
                <button class="delete-tag-btn" data-region-id="${r.id}">Delete</button>
            </div>
        `;
        previousTags.appendChild(div);
    });
    
    // Add event listeners to delete buttons
    document.querySelectorAll('.delete-tag-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const regionId = parseInt(this.getAttribute('data-region-id'));
            deleteTag(regionId);
        });
    });
}

// Delete tag
function deleteTag(regionId) {
    // Save current state for undo
    historyStack.push({
        selected: new Set(selected),
        regions: JSON.parse(JSON.stringify(REGIONS))
    });
    
    // Find the region and remove its tag
    const region = REGIONS.find(r => r.id === regionId);
    if (region) {
        region.tag = null;
        region.bidItem = null;
        region.reason = null;
        region.auto_tagged = false;
    }
    
    // Update the display
    redraw();
    updatePreviousTagsDisplay();
}

// Redraw canvas
function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    
    // Draw debug grid
    if (debugMode) {
        ctx.strokeStyle = 'rgba(200,200,200,0.3)';
        ctx.beginPath();
        for(let x = 0; x < canvas.width; x += 50) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
        }
        for(let y = 0; y < canvas.height; y += 50) {
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
        }
        ctx.stroke();
    }

    REGIONS.forEach(r => {
        const xs = r.pts.map(p => p[0]);
        const ys = r.pts.map(p => p[1]);
        const xMin = Math.min(...xs);
        const yMin = Math.min(...ys);
        
        // Draw region background if tagged
        if (r.tag) {
            // Use different colors for auto-tagged vs manually tagged
            ctx.fillStyle = r.auto_tagged ? 'rgba(33,150,243,0.2)' : 'rgba(255,0,0,0.2)';
            ctx.beginPath();
            r.pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
            ctx.closePath();
            ctx.fill();
        }

        // Draw region outline
        ctx.strokeStyle = selected.has(r.id) ? 'lime' : 'blue';
        ctx.lineWidth = selected.has(r.id) ? 3 : 2;
        ctx.beginPath();
        r.pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
        ctx.closePath();
        ctx.stroke();

        // Draw text and tag if present
        if (r.tag || debugMode) {
            ctx.fillStyle = r.auto_tagged ? '#2196F3' : 'red';
            ctx.font = '14px sans-serif';
            let label = r.tag ? `${typeof r.tag === 'string' ? r.tag : r.tag.value}(${r.bidItem === 'Yes' ? 'yes' : 'no'})` : '';
            if (r.auto_tagged) {
                label = '🔄 ' + label;  // Add auto-tag indicator
            }
            if (debugMode) {
                label = `${label} [${r.id}]`;
            }
            ctx.fillText(label, xMin, yMin - 2);

            // Draw OCR text in debug mode
            if (debugMode) {
                ctx.fillStyle = '#666';
                ctx.font = '12px sans-serif';
                ctx.fillText(r.text || '', xMin, yMin + 12);
            }
        }
    });
}

// Select/deselect regions
canvas.addEventListener('click', e => {
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    
    updateDebugInfo(cx, cy);
    
    let found = false;
    REGIONS.forEach(r => {
        const xs = r.pts.map(p => p[0]);
        const ys = r.pts.map(p => p[1]);
        const xMin = Math.min(...xs);
        const xMax = Math.max(...xs);
        const yMin = Math.min(...ys);
        const yMax = Math.max(...ys);
        
        if (cx >= xMin && cx <= xMax && cy >= yMin && cy <= yMax) {
            found = true;
            if (selected.has(r.id)) {
                selected.delete(r.id);
            } else {
                selected.add(r.id);
            }
        }
    });
    
    if (found) {
        redraw();
    }
});

// Toggle debug mode
document.getElementById('toggleDebug').onclick = () => {
    debugMode = !debugMode;
    debugInfo.style.display = debugMode ? 'block' : 'none';
    redraw();
};

// Keyboard shortcuts
document.addEventListener('keydown', e => {
    // Don't process keyboard shortcuts when typing in inputs or textarea
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    const key = e.key.toUpperCase();
    
    if (key === 'T' && selected.size > 0) {
        e.preventDefault(); // Prevent 'T' from appearing in input
        // Save current state for undo
        historyStack.push({
            selected: new Set(selected),
            regions: JSON.parse(JSON.stringify(REGIONS))
        });
        
        // Show scope input near first selected region
        const firstRegion = REGIONS.find(r => selected.has(r.id));
        const xs = firstRegion.pts.map(p => p[0]);
        const ys = firstRegion.pts.map(p => p[1]);
        const xMin = Math.min(...xs);
        const yMin = Math.min(...ys);
        
        const rect = canvas.getBoundingClientRect();
        scopeInput.style.left = (rect.left + xMin) + 'px';
        scopeInput.style.top = (rect.top + window.scrollY + yMin - 30) + 'px';
        scopeInput.style.display = 'block';
        scopeInput.value = '';  // Ensure input is empty
        scopeInput.focus();
        
        pendingTag = {
            regions: Array.from(selected),
            stage: 'scope'
        };
    }
    
    else if (key === 'U' && historyStack.length > 0) {
        const prev = historyStack.pop();
        selected = prev.selected;
        REGIONS.forEach((r, i) => {
            if (prev.regions[i]) {
                r.tag = prev.regions[i].tag;
                r.bidItem = prev.regions[i].bidItem;
                r.reason = prev.regions[i].reason;
                r.auto_tagged = prev.regions[i].auto_tagged;
            }
        });
        redraw();
        updatePreviousTagsDisplay();
    }
    
    else if (key === 'S') {
        document.getElementById('saveBtn').click();
    }
    
    else if (key === 'R') {
        document.getElementById('resetBtn').click();
    }
    
    else if (key === 'P') {
        document.getElementById('prevFigureBtn').click();
    }
});

// Handle scope input
scopeInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && pendingTag) {
        const scope = scopeInput.value.trim();
        if (scope) {
            scopeInput.style.display = 'none';
            
            // Check if the scope is in the predefined list or "Others"
            if (!SCOPES.includes(scope) && scope !== "Others") {
                alert('Please select a scope from the predefined list or "Others".');
                // Reset and show the input again
                const rect = canvas.getBoundingClientRect();
                const firstRegion = REGIONS.find(r => selected.has(r.id));
                const xs = firstRegion.pts.map(p => p[0]);
                const ys = firstRegion.pts.map(p => p[1]);
                const xMin = Math.min(...xs);
                const yMin = Math.min(...ys);
                
                scopeInput.style.left = (rect.left + xMin) + 'px';
                scopeInput.style.top = (rect.top + window.scrollY + yMin - 30) + 'px';
                scopeInput.style.display = 'block';
                scopeInput.focus();
                return;
            }
            
            // If "Others" is selected, prompt for custom scope name
            if (scope === "Others") {
                const customScope = prompt("Enter custom scope name:");
                if (customScope && customScope.trim()) {
                    pendingTag.scope = customScope.trim();
                } else {
                    // If user cancels or enters empty string, use "Others"
                    pendingTag.scope = "Others";
                }
            } else {
                pendingTag.scope = scope;
            }
            
            // Show bid item input
            const rect = canvas.getBoundingClientRect();
            bidInput.style.left = scopeInput.style.left;
            bidInput.style.top = scopeInput.style.top;
            bidInput.style.display = 'block';
            bidInput.value = '';
            bidInput.focus();
            
            pendingTag.stage = 'bidItem';
        }
    }
    else if (e.key === 'Escape') {
        scopeInput.style.display = 'none';
        pendingTag = null;
    }
});

// Handle bid item input
bidInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && pendingTag) {
        e.preventDefault(); // Prevent default behavior
        const bid = bidInput.value.trim().toLowerCase();
        if (bid === 'y' || bid === 'n') {
            bidInput.style.display = 'none';
            pendingTag.bidItem = bid === 'y' ? 'Yes' : 'No';
            
            // Show reason input
            const rect = canvas.getBoundingClientRect();
            reasonInput.style.left = bidInput.style.left;
            reasonInput.style.top = bidInput.style.top;
            reasonInput.style.display = 'block';
            reasonInput.value = '';
            reasonInput.focus();
            
            pendingTag.stage = 'reason';
        }
    }
    else if (e.key === 'Escape') {
        bidInput.style.display = 'none';
        pendingTag = null;
    }
});

// Handle reason input
reasonInput.addEventListener('keydown', e => {
    // Allow normal typing in the textarea, only handle Enter and Escape
    if (e.key === 'Enter' && !e.shiftKey && pendingTag) {
        e.preventDefault(); // Prevent newline in textarea
        const reason = reasonInput.value.trim();
        reasonInput.style.display = 'none';
        
        // Get combined text from all selected regions
        const combinedText = pendingTag.regions
            .map(id => REGIONS.find(r => r.id === id))
            .filter(r => r && r.text)
            .map(r => r.text)
            .join(' ');
        
        // Apply tag to all selected regions
        pendingTag.regions.forEach(id => {
            const region = REGIONS.find(r => r.id === id);
            region.tag = pendingTag.scope;
            region.bidItem = pendingTag.bidItem;
            region.reason = reason;
            region.auto_tagged = false;  // Manually tagged
            region.combinedText = combinedText;  // Store combined text
        });
        
        selected.clear();
        pendingTag = null;
        redraw();
        updatePreviousTagsDisplay();
    }
    else if (e.key === 'Escape') {
        reasonInput.style.display = 'none';
        pendingTag = null;
    }
});

// Save button handler
document.getElementById('saveBtn').onclick = () => {
    // Extract keywords-to-scope mapping
    const keywordMappings = [];
    const processedTexts = new Set();
    
    REGIONS.forEach(r => {
        if (r.tag) {
            // Use combined text if available, otherwise individual text
            const text = r.combinedText || r.text || '';
            
            // Avoid duplicates
            const key = `${text}-${r.tag}-${r.bidItem}`;
            if (!processedTexts.has(key) && text) {
                processedTexts.add(key);
                keywordMappings.push({
                    text: text,
                    scope: r.tag,
                    bidItem: r.bidItem,
                    reason: r.reason || '',
                    auto_tagged: r.auto_tagged || false,
                    auto_source: r.auto_source || ''
                });
            }
        }
    });
    
    fetch('/save_crop_annotations', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            upload_id: UPLOAD_ID,
            page_num: PAGE_NUM,
            crop_idx: CROP_IDX,
            regions: REGIONS,
            keyword_mappings: keywordMappings
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            window.location.href = data.next_url;
        }
    });
};

// Save Only button handler
document.getElementById('saveOnlyBtn').onclick = () => {
    // Extract keywords-to-scope mapping
    const keywordMappings = [];
    const processedTexts = new Set();
    
    REGIONS.forEach(r => {
        if (r.tag) {
            // Use combined text if available, otherwise individual text
            const text = r.combinedText || r.text || '';
            
            // Avoid duplicates
            const key = `${text}-${r.tag}-${r.bidItem}`;
            if (!processedTexts.has(key) && text) {
                processedTexts.add(key);
                keywordMappings.push({
                    text: text,
                    scope: r.tag,
                    bidItem: r.bidItem,
                    reason: r.reason || '',
                    auto_tagged: r.auto_tagged || false,
                    auto_source: r.auto_source || ''
                });
            }
        }
    });
    
    // Show a loading indicator
    const loadingMsg = document.createElement('div');
    loadingMsg.textContent = 'Saving and updating auto-tags...';
    loadingMsg.style.position = 'fixed';
    loadingMsg.style.top = '20px';
    loadingMsg.style.left = '50%';
    loadingMsg.style.transform = 'translateX(-50%)';
    loadingMsg.style.backgroundColor = '#2196F3';
    loadingMsg.style.color = 'white';
    loadingMsg.style.padding = '10px 20px';
    loadingMsg.style.borderRadius = '4px';
    loadingMsg.style.zIndex = '1000';
    document.body.appendChild(loadingMsg);
    
    fetch('/save_crop_annotations', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            upload_id: UPLOAD_ID,
            page_num: PAGE_NUM,
            crop_idx: CROP_IDX,
            regions: REGIONS,
            keyword_mappings: keywordMappings,
            stay_on_page: true
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            // Refresh the page to show updated auto-tags
            window.location.href = data.next_url;
        } else {
            // Show error message
            document.body.removeChild(loadingMsg);
            const errorMsg = document.createElement('div');
            errorMsg.textContent = data.message || 'Error saving annotations';
            errorMsg.style.position = 'fixed';
            errorMsg.style.top = '20px';
            errorMsg.style.left = '50%';
            errorMsg.style.transform = 'translateX(-50%)';
            errorMsg.style.backgroundColor = '#F44336';
            errorMsg.style.color = 'white';
            errorMsg.style.padding = '10px 20px';
            errorMsg.style.borderRadius = '4px';
            errorMsg.style.zIndex = '1000';
            document.body.appendChild(errorMsg);
            
            // Remove the message after 3 seconds
            setTimeout(() => {
                document.body.removeChild(errorMsg);
            }, 3000);
        }
    })
    .catch(error => {
        // Remove loading message and show error
        document.body.removeChild(loadingMsg);
        const errorMsg = document.createElement('div');
        errorMsg.textContent = 'Network error occurred';
        errorMsg.style.position = 'fixed';
        errorMsg.style.top = '20px';
        errorMsg.style.left = '50%';
        errorMsg.style.transform = 'translateX(-50%)';
        errorMsg.style.backgroundColor = '#F44336';
        errorMsg.style.color = 'white';
        errorMsg.style.padding = '10px 20px';
        errorMsg.style.borderRadius = '4px';
        errorMsg.style.zIndex = '1000';
        document.body.appendChild(errorMsg);
        
        // Remove the message after 3 seconds
        setTimeout(() => {
            document.body.removeChild(errorMsg);
        }, 3000);
    });
};

// Reset button handler
document.getElementById('resetBtn').onclick = () => {
    selected.clear();
    redraw();
};

// Previous Figure button handler
document.getElementById('prevFigureBtn').onclick = () => {
    // If we're on the first figure of the page
    if (CROP_IDX === 0) {
        // If we're on the first page, stay here
        if (PAGE_NUM === 1) {
            alert('This is the first figure of the first page.');
            return;
        }
        
        // Otherwise, go to the previous page
        // We'll navigate to the sheet progress page and let the user select the last figure
        window.location.href = `/sheet_progress/${UPLOAD_ID}/${PAGE_NUM - 1}`;
    } else {
        // Go to the previous figure on the same page
        window.location.href = `/annotate_crop/${UPLOAD_ID}/${PAGE_NUM}/${CROP_IDX - 1}`;
    }
}; 