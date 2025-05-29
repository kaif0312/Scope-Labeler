function confirmDelete(uploadId, filename) {
    document.getElementById('deleteMessage').textContent = 
        `Are you sure you want to delete "${filename}"?`;
    document.getElementById('deleteForm').action = 
        `/project/${window.location.pathname.split('/')[2]}/delete_pdf?upload_id=` + uploadId;
    document.getElementById('deleteModal').style.display = 'flex';
}

function hideDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == document.getElementById('deleteModal')) {
        hideDeleteModal();
    }
} 