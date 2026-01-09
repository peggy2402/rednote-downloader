document.getElementById('downloadBtn').addEventListener('click', async () => {
    const urlInput = document.getElementById('urlInput').value.trim();
    const resultContainer = document.getElementById('resultContainer');
    const resultContent = document.getElementById('resultContent');
    const errorContainer = document.getElementById('errorContainer');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorText = document.getElementById('errorText');

    // Reset previous results/errors
    resultContainer.style.display = 'none';
    errorContainer.style.display = 'none';
    loadingSpinner.style.display = 'none';

    if (!urlInput) {
        showError('Vui lòng nhập một URL hợp lệ.');
        return;
    }

    // Show loading state
    const btn = document.getElementById('downloadBtn');
    const originalText = btn.innerHTML;
    loadingSpinner.style.display = 'block';
    btn.disabled = true;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();

        if (data.success) {
            const title = data.data.title || 'Download';
            if (data.data.type === 'video') {
                const mediaUrl = data.data.media_url;
                const viewUrl = data.data.view_url || mediaUrl;
                resultContent.innerHTML = `
                    <p><strong>Tiêu đề:</strong> ${title}</p>
                    <div class="ratio ratio-16x9 mb-3">
                        <video controls style="border-radius: 8px;">
                            <source src="${mediaUrl}" type="video/mp4">
                            Trình duyệt của bạn không hỗ trợ video.
                        </video>
                    </div>
                    <p><strong>Link trực tiếp:</strong><br>
                        <small class="text-muted break-word">${mediaUrl}</small>
                    </p>
                    <div class="d-flex gap-2 flex-wrap">
                        <a href="/download?url=${encodeURIComponent(mediaUrl)}" class="btn btn-success">
                            <i class="fas fa-download"></i> Tải xuống
                        </a>
                        <a href="${viewUrl}" target="_blank" class="btn btn-outline-primary">
                            <i class="fas fa-external-link-alt"></i> Xem trên XHS
                        </a>
                    </div>
                    <small class="d-block mt-2 text-muted">Nếu tải xuống không hoạt động, hãy nhấp chuột phải vào "Link trực tiếp" và chọn "Lưu liên kết dưới dạng..."</small>
                `;
            } else if (data.data.type === 'image' || Array.isArray(data.data.media_urls)) {
                const images = data.data.media_urls || [];
                const count = data.data.count || images.length;
                let imgsHtml = `
                    <p><strong>Tiêu đề:</strong> ${title}</p>
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <p class="mb-0"><strong>Tổng số ảnh:</strong> <span class="badge bg-primary">${count}</span></p>
                        <small class="text-muted">Cuộn sang phải để xem thêm</small>
                    </div>
                    <div class="d-flex flex-row overflow-auto gap-3 gallery" style="padding: 10px 0;">
                `;
                images.forEach((img, idx) => {
                    imgsHtml += `
                        <div class="text-center flex-shrink-0" style="min-width:190px">
                            <a href="${img}" target="_blank" class="d-block mb-2">
                                <img src="${img}" class="rounded border" style="max-width:180px; max-height:220px; object-fit:cover; cursor:pointer; transition: transform 0.2s;" 
                                     onmouseover="this.style.transform='scale(1.05)'" 
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Image ${idx + 1}">
                            </a>
                            <div class="d-flex gap-1 justify-content-center flex-wrap">
                                <a href="/download?url=${encodeURIComponent(img)}" class="btn btn-sm btn-success" title="Tải ảnh này">
                                    <i class="fas fa-download"></i>
                                </a>
                                <a href="${img}" target="_blank" class="btn btn-sm btn-outline-primary" title="Xem ảnh">
                                    <i class="fas fa-eye"></i>
                                </a>
                            </div>
                            <small class="d-block mt-1 text-muted">Ảnh #${idx + 1}</small>
                        </div>
                    `;
                });
                imgsHtml += `</div>`;
                resultContent.innerHTML = imgsHtml;
            } else {
                // Fallback: show raw JSON
                resultContent.innerHTML = `<pre>${JSON.stringify(data.data, null, 2)}</pre>`;
            }
            resultContainer.style.display = 'block';
        } else {
            showError(data.error || 'Không thể xử lý liên kết này.');
        }
    } catch (error) {
        showError('Lỗi mạng. Vui lòng kiểm tra kết nối của bạn và thử lại.');
        console.error('Error:', error);
    } finally {
        // Restore button state
        loadingSpinner.style.display = 'none';
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    const errorText = document.getElementById('errorText');
    errorText.textContent = message;
    errorContainer.style.display = 'block';
}