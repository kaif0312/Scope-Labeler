document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            this.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
    
    // Search functionality for scopes
    const scopeSearch = document.getElementById('scopeSearch');
    const scopeRows = document.querySelectorAll('.scope-row');
    const rowsPerPage = 20;
    let currentPage = 1;
    
    function filterScopes() {
        const searchTerm = scopeSearch.value.toLowerCase();
        let visibleCount = 0;
        
        scopeRows.forEach(row => {
            const scopeName = row.cells[0].textContent.toLowerCase();
            if (scopeName.includes(searchTerm)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
        
        // Reset pagination when searching
        if (searchTerm) {
            document.getElementById('scopePagination').style.display = 'none';
        } else {
            document.getElementById('scopePagination').style.display = 'flex';
            updatePagination();
            goToPage(1);
        }
    }
    
    if (scopeSearch) {
        scopeSearch.addEventListener('input', filterScopes);
    }
    
    // Pagination for scopes
    function updatePagination() {
        const totalPages = Math.ceil(scopeRows.length / rowsPerPage);
        const pagination = document.getElementById('scopePagination');
        pagination.innerHTML = '';
        
        // Previous button
        const prevButton = document.createElement('button');
        prevButton.textContent = '←';
        prevButton.addEventListener('click', () => {
            if (currentPage > 1) goToPage(currentPage - 1);
        });
        pagination.appendChild(prevButton);
        
        // Page buttons
        for (let i = 1; i <= totalPages; i++) {
            const pageButton = document.createElement('button');
            pageButton.textContent = i;
            if (i === currentPage) pageButton.classList.add('active');
            pageButton.addEventListener('click', () => goToPage(i));
            pagination.appendChild(pageButton);
            
            // Add ellipsis for many pages
            if (totalPages > 10) {
                if (i === 1 || i === totalPages || 
                    (i >= currentPage - 1 && i <= currentPage + 1)) {
                    // Show these page numbers
                } else if (i === 2 || i === totalPages - 1) {
                    pageButton.textContent = '...';
                    i = i === 2 ? currentPage - 2 : totalPages - 1;
                } else {
                    pagination.removeChild(pageButton);
                }
            }
        }
        
        // Next button
        const nextButton = document.createElement('button');
        nextButton.textContent = '→';
        nextButton.addEventListener('click', () => {
            if (currentPage < totalPages) goToPage(currentPage + 1);
        });
        pagination.appendChild(nextButton);
    }
    
    function goToPage(page) {
        currentPage = page;
        const start = (page - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        
        scopeRows.forEach((row, index) => {
            if (index >= start && index < end) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
        
        // Update active button
        document.querySelectorAll('#scopePagination button').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent == page) btn.classList.add('active');
        });
    }
    
    // Initialize pagination if there are scope rows
    if (scopeRows.length > 0) {
        updatePagination();
        goToPage(1);
    }
    
    // Keywords modal functionality
    const modal = document.getElementById('keywordsModal');
    const modalTitle = document.getElementById('modalTitle');
    const keywordsContainer = document.getElementById('keywordsContainer');
    const keywordSearch = document.getElementById('keywordSearch');
    const closeBtn = document.querySelector('.close-btn');
    
    // Close modal when clicking the close button
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // View keywords buttons
    document.querySelectorAll('.view-keywords-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const scope = btn.dataset.scope;
            const project = btn.dataset.project;
            
            showKeywordsForScope(scope, project);
        });
    });
    
    // Filter keywords in modal
    if (keywordSearch) {
        keywordSearch.addEventListener('input', () => {
            const searchTerm = keywordSearch.value.toLowerCase();
            const keywordItems = document.querySelectorAll('.keyword-item');
            
            keywordItems.forEach(item => {
                const text = item.querySelector('.keyword-text').textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    function showKeywordsForScope(scope, projectFilter) {
        // Set modal title
        if (projectFilter === 'all') {
            modalTitle.textContent = `Keywords for "${scope}" (All Projects)`;
        } else {
            modalTitle.textContent = `Keywords for "${scope}" in "${projectFilter}"`;
        }
        
        // Clear previous content
        keywordsContainer.innerHTML = '';
        if (keywordSearch) keywordSearch.value = '';
        
        // Get keywords for this scope
        const keywords = scopeKeywords[scope] || [];
        
        if (keywords.length === 0) {
            keywordsContainer.innerHTML = '<p>No keywords found for this scope.</p>';
        } else {
            // Filter by project if needed
            const filteredKeywords = projectFilter === 'all' 
                ? keywords 
                : keywords.filter(k => k.project_name === projectFilter);
            
            if (filteredKeywords.length === 0) {
                keywordsContainer.innerHTML = '<p>No keywords found for this scope in this project.</p>';
            } else {
                // Create keyword items
                filteredKeywords.forEach(keyword => {
                    const keywordItem = document.createElement('div');
                    keywordItem.className = 'keyword-item';
                    
                    const bidBadge = keyword.bid_item === 'Yes' 
                        ? '<span class="badge badge-yes">Bid: Yes</span>' 
                        : '<span class="badge badge-no">Bid: No</span>';
                    
                    let reasonHtml = '';
                    if (keyword.reason) {
                        reasonHtml = `<div class="keyword-reason">"${keyword.reason}"</div>`;
                    }
                    
                    keywordItem.innerHTML = `
                        <div class="keyword-text">${keyword.text}</div>
                        <div class="keyword-meta">
                            ${bidBadge}
                            <span>Project: ${keyword.project_name}</span>
                            <span>PDF: ${keyword.pdf_name}</span>
                        </div>
                        ${reasonHtml}
                    `;
                    
                    keywordsContainer.appendChild(keywordItem);
                });
            }
        }
        
        // Show modal
        modal.style.display = 'flex';
    }
    
    // Create chart if Chart.js is loaded
    if (typeof Chart !== 'undefined' && topScopes && topScopes.length > 0) {
        const ctx = document.getElementById('topScopesChart').getContext('2d');
        
        // Extract data for chart
        const labels = topScopes.map(item => item[0]);
        const data = topScopes.map(item => item[1].count);
        const bidYesData = topScopes.map(item => item[1].bid_yes);
        const bidNoData = topScopes.map(item => item[1].bid_no);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Keywords',
                        data: data,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Bid Yes',
                        data: bidYesData,
                        backgroundColor: 'rgba(75, 192, 192, 0.5)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Bid No',
                        data: bidNoData,
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}); 