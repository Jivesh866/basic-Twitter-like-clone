document.addEventListener("DOMContentLoaded", function () {
    // --- 1. HANDLE LIKES DYNAMICALLY ---
    document.querySelectorAll(".like-btn").forEach(button => {
        button.addEventListener("click", function () {
            const postId = this.getAttribute("data-post-id");
            const likeCountSpan = this.querySelector(".like-count");

            fetch(`/like/${postId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update like count text
                    likeCountSpan.textContent = data.new_likes;
                    
                    // Toggle button styling and heart icon based on server response
                    if (data.liked) {
                        this.innerHTML = `❤️ Liked (<span class="like-count">${data.new_likes}</span>)`;
                    } else {
                        this.innerHTML = `🤍 Like (<span class="like-count">${data.new_likes}</span>)`;
                    }
                } else {
                    alert("Error liking post. Make sure you are logged in.");
                }
            })
            .catch(error => console.error("Error:", error));
        });
    });

    // --- 2. HANDLE COMMENTS DYNAMICALLY ---
    document.querySelectorAll(".comment-form").forEach(form => {
        form.addEventListener("submit", function (e) {
            e.preventDefault(); 

            const postId = this.getAttribute("data-post-id");
            const inputField = this.querySelector(".comment-input");
            const commentText = inputField.value;

            fetch(`/comment/${postId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: `comment=${encodeURIComponent(commentText)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const postCard = document.getElementById(`post-${postId}`);
                    const commentsList = postCard.querySelector(".comments-list");
                    
                    const noCommentsMsg = commentsList.querySelector(".no-comments-text");
                    if (noCommentsMsg) {
                        noCommentsMsg.remove();
                    }

                    const newCommentHtml = `
                        <div class="border-bottom pb-2 mb-2">
                            <div class="d-flex justify-content-between">
                                <p class="small text-muted mb-1"><strong>@${data.username}</strong></p>
                                <small class="text-muted">just now</small>
                            </div>
                            <p class="small mb-0">${data.content}</p>
                        </div>
                    `;

                    commentsList.insertAdjacentHTML("beforeend", newCommentHtml);
                    inputField.value = "";
                } else {
                    alert("Error posting comment.");
                }
            })
            .catch(error => console.error("Error:", error));
        });
    });
});