function showCreateProjectModal() {
    document.getElementById('createProjectModal').style.display = 'flex';
}

function hideCreateProjectModal() {
    document.getElementById('createProjectModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == document.getElementById('createProjectModal')) {
        hideCreateProjectModal();
    }
} 