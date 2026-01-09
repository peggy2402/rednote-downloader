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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();

        if (data.success) {
            const title = data.data.title || 'Download';
            
            if (data.data.type === 'video') {
                const mediaUrl = data.data.media_url;
                const viewUrl = data.data.view_url || mediaUrl;
                const originUrl = data.data.origin_url || urlInput;
                
                // Tạo proxy URL cho video stream
                const proxyVideoUrl = `/video_stream?url=${encodeURIComponent(mediaUrl)}`;
                
                resultContent.innerHTML = `
                    <p><strong>Tiêu đề:</strong> ${title}</p>
                    <div class="ratio ratio-16x9 mb-3">
                        <video controls style="border-radius: 8px; width: 100%;" preload="metadata" crossorigin="anonymous">
                            <source src="${proxyVideoUrl}" type="video/mp4">
                            Trình duyệt của bạn không hỗ trợ video tag.
                        </video>
                    </div>
                    <p><strong>Link gốc:</strong><br>
                        <small class="text-muted break-word" style="word-break: break-all;">${mediaUrl}</small>
                    </p>
                    <div class="d-flex gap-2 flex-wrap">
                        <a href="/download?url=${encodeURIComponent(mediaUrl)}" class="btn btn-success">
                            <i class="fas fa-download"></i> Tải video
                        </a>
                        <a href="${originUrl}" target="_blank" class="btn btn-outline-primary">
                            <i class="fas fa-external-link-alt"></i> Xem bài gốc
                        </a>
                        <button class="btn btn-outline-info" onclick="copyToClipboard('${mediaUrl.replace(/'/g, "\\'")}')">
                            <i class="fas fa-copy"></i> Copy link
                        </button>
                    </div>
                    <small class="d-block mt-2 text-muted">
                        <i class="fas fa-info-circle"></i> Nếu video không phát, hãy thử tải xuống.
                    </small>
                `;
                
                // Tự động play video sau khi load
                setTimeout(() => {
                    const video = resultContent.querySelector('video');
                    if (video) {
                        video.load();
                    }
                }, 500);
            } else if (data.data.type === 'image' || Array.isArray(data.data.media_urls)) {
                const images = data.data.media_urls || [];
                const count = data.data.count || images.length;
                
                // Detect mobile device
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                
                let imgsHtml = `
                    <p><strong>Tiêu đề:</strong> ${title}</p>
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <p class="mb-0"><strong>Tổng số ảnh:</strong> <span class="badge bg-primary">${count}</span></p>
                        ${isMobile ? 
                            `<button class="btn btn-sm btn-outline-secondary" id="downloadAllBtn" data-images='${JSON.stringify(images).replace(/'/g, "&apos;")}'>
                                <i class="fas fa-download"></i> Tải tất cả
                            </button>` :
                            `<button class="btn btn-sm btn-success" id="downloadZipBtn" data-images='${JSON.stringify(images).replace(/'/g, "&apos;")}'>
                                <i class="fas fa-file-archive"></i> Tải ZIP
                            </button>`
                        }
                    </div>
                    <div class="d-flex flex-row overflow-auto gap-3 gallery" style="padding: 10px 0;">
                `;
                images.forEach((img, idx) => {
                    // Sử dụng proxy cho ảnh
                    const proxyUrl = `/proxy-image?url=${encodeURIComponent(img)}`;
                    imgsHtml += `
                        <div class="text-center flex-shrink-0" style="min-width:190px">
                            <a href="${img}" target="_blank" class="d-block mb-2">
                                <img src="${proxyUrl}" 
                                     class="rounded border" 
                                     style="max-width:180px; max-height:220px; object-fit:cover; cursor:pointer;" 
                                     loading="lazy"
                                     alt="Image ${idx + 1}"
                                     onerror="this.style.display='none'; this.parentElement.innerHTML+='<p class=text-danger>Lỗi tải ảnh</p>'">
                            </a>
                            <div class="d-flex gap-1 justify-content-center flex-wrap">
                                <a href="/download?url=${encodeURIComponent(img)}" 
                                   class="btn btn-sm btn-success" title="Tải ảnh này">
                                    <i class="fas fa-download"></i>
                                </a>
                                <a href="${img}" target="_blank" class="btn btn-sm btn-outline-primary" title="Xem ảnh gốc">
                                    <i class="fas fa-eye"></i>
                                </a>
                            </div>
                            <small class="d-block mt-1 text-muted">Ảnh #${idx + 1}</small>
                        </div>
                    `;
                });
                imgsHtml += `</div>`;
                resultContent.innerHTML = imgsHtml;
                
                // Thêm event listeners
                setTimeout(() => {
                    // Nút "Tải tất cả" (mobile)
                    const allBtn = document.getElementById('downloadAllBtn');
                    if (allBtn) {
                        allBtn.addEventListener('click', (e) => {
                            e.preventDefault();
                            const imgStr = allBtn.getAttribute('data-images');
                            try {
                                const urls = JSON.parse(imgStr);
                                downloadAllImages(urls);
                            } catch (err) {
                                console.error('Parse error:', err);
                                showError('Lỗi: Không thể parse dữ liệu ảnh. ' + err.message);
                            }
                        });
                    }
                    
                    // Nút "Tải ZIP" (desktop)
                    const zipBtn = document.getElementById('downloadZipBtn');
                    if (zipBtn) {
                        zipBtn.addEventListener('click', (e) => {
                            e.preventDefault();
                            const imgStr = zipBtn.getAttribute('data-images');
                            try {
                                const urls = JSON.parse(imgStr);
                                downloadAsZip(urls);
                            } catch (err) {
                                console.error('Parse error:', err);
                                showError('Lỗi: Không thể parse dữ liệu ảnh. ' + err.message);
                            }
                        });
                    }
                }, 100);
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
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});
// Thêm hàm helper mới
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Đã copy link vào clipboard!');
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

function downloadAllImages(urls) {
    console.log('downloadAllImages called with:', urls);
    
    if (!urls || urls.length === 0) {
        showError('Không có ảnh để tải xuống.');
        return;
    }
    
    console.log(`Starting download of ${urls.length} images`);
    
    // Hiển thị thông báo bắt đầu
    const resultContainer = document.getElementById('resultContainer');
    const originalContent = resultContainer.innerHTML;
    
    const progressMsg = document.createElement('div');
    progressMsg.className = 'alert alert-info mt-3';
    progressMsg.innerHTML = `
        <i class="fas fa-download"></i> 
        <strong>Đang tải ${urls.length} ảnh...</strong>
        <div class="progress mt-2" style="height: 20px;">
            <div id="downloadProgress" class="progress-bar bg-success" role="progressbar" style="width: 0%">
                <span id="progressText">0/${urls.length}</span>
            </div>
        </div>
    `;
    resultContainer.appendChild(progressMsg);
    
    let completed = 0;
    
    urls.forEach((url, index) => {
        setTimeout(() => {
            console.log(`Downloading image ${index + 1}/${urls.length}: ${url}`);
            
            const link = document.createElement('a');
            link.href = `/download?url=${encodeURIComponent(url)}`;
            link.download = '';
            
            document.body.appendChild(link);
            link.click();
            
            // Cleanup sau một chút
            setTimeout(() => {
                document.body.removeChild(link);
            }, 100);
            
            // Update progress bar
            completed++;
            const percent = Math.round((completed / urls.length) * 100);
            const progressBar = document.getElementById('downloadProgress');
            const progressText = document.getElementById('progressText');
            if (progressBar) progressBar.style.width = percent + '%';
            if (progressText) progressText.textContent = `${completed}/${urls.length}`;
            
            // Thông báo hoàn thành
            if (completed === urls.length) {
                console.log('All downloads completed!');
                progressMsg.innerHTML = `
                    <i class="fas fa-check-circle text-success"></i> 
                    <strong>✓ Đã tải xong ${urls.length} ảnh!</strong>
                    <p class="mb-0 mt-2"><small>Nếu trình duyệt chặn, hãy cho phép downloads từ trang này.</small></p>
                `;
            }
        }, index * 300);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showError('✓ Đã copy link!');
        setTimeout(() => {
            document.getElementById('errorContainer').style.display = 'none';
        }, 2000);
    });
}

function downloadAsZip(urls) {
    console.log('downloadAsZip called with:', urls.length, 'images');
    
    if (!urls || urls.length === 0) {
        showError('Không có ảnh để tải xuống.');
        return;
    }
    
    // Hiển thị progress
    const resultContainer = document.getElementById('resultContainer');
    const progressMsg = document.createElement('div');
    progressMsg.className = 'alert alert-info mt-3';
    progressMsg.innerHTML = `
        <i class="fas fa-spinner fa-spin"></i> 
        <strong>Đang chuẩn bị ZIP...</strong>
    `;
    resultContainer.appendChild(progressMsg);
    
    // Gửi request tới /download-all
    fetch('/download-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ urls: urls })
    })
    .then(response => {
        if (!response.ok) throw new Error('Server error');
        
        // Download ZIP
        return response.blob().then(blob => {
            const timestamp = new Date().toISOString().slice(0, 10);
            const filename = `xiaohongshu_images_${timestamp}.zip`;
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Success message
            progressMsg.innerHTML = `
                <i class="fas fa-check-circle text-success"></i> 
                <strong>✓ Đã tải ZIP ${urls.length} ảnh!</strong>
                <p class="mb-0 mt-2"><small>File: <code>${filename}</code></small></p>
            `;
        });
    })
    .catch(error => {
        console.error('ZIP download error:', error);
        progressMsg.innerHTML = `
            <i class="fas fa-exclamation-circle text-danger"></i> 
            <strong>Lỗi tải ZIP</strong>
            <p class="mb-0 mt-2"><small>${error.message}</small></p>
        `;
    });
}

function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    const errorText = document.getElementById('errorText');
    errorText.textContent = message;
    errorContainer.style.display = 'block';
}