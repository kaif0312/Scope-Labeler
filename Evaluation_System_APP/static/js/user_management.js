function confirmDelete(userId, username) {
    document.getElementById('deleteMessage').textContent = 
        `Are you sure you want to delete user "${username}"?`;
    document.getElementById('deleteForm').action = 
        `/delete_user?user_id=${userId}`;
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