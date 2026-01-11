async function pasteClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        document.getElementById('urlInput').value = text;
    } catch (e) { alert("Vui lòng dán thủ công!"); }
}

async function handleDownload() {
    const urlInput = document.getElementById('urlInput');
    const loading = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const errorMsg = document.getElementById('error-msg');
    const btn = document.getElementById('downloadBtn');
    
    const url = urlInput.value.trim();
    if (!url) { showError("Chưa nhập link!"); return; }

    resultDiv.classList.add('hidden');
    errorMsg.classList.add('hidden');
    loading.classList.remove('hidden');
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = "Đang xử lý...";

    try {
        const response = await fetch('/api/get-info', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url: url })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Lỗi tải dữ liệu");
        
        renderResult(data, url);

    } catch (error) {
        showError(error.message);
    } finally {
        loading.classList.add('hidden');
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = "Lấy Link Tải";
    }
}

function renderResult(data, originalUrl) {
    const resultDiv = document.getElementById('result');
    const timestamp = Date.now();
    
    // PROXY AVATAR: Fix lỗi không hiện ảnh đại diện
    const avatarSrc = data.avatar ? `/proxy-image?url=${encodeURIComponent(data.avatar)}` : 'https://via.placeholder.com/50';

    let mediaHtml = '';
    let buttonsHtml = '';

    if (data.type === 'video') {
        const videoProxy = `/proxy-download?url=${encodeURIComponent(data.download_url)}&filename=video_${timestamp}.mp4`;
        mediaHtml = `
            <div class="video-wrapper">
                <video controls poster="/proxy-image?url=${encodeURIComponent(data.cover)}">
                    <source src="${data.download_url}" type="video/mp4">
                    <source src="${videoProxy}" type="video/mp4">
                </video>
            </div>`;
        buttonsHtml = `
            <a href="${videoProxy}" class="btn-primary">
                <i class="fas fa-download"></i> Tải Video MP4
            </a>`;
    } else {
        const imagesHtml = data.images.map((img) => `
            <div class="scroll-item">
                <img src="/proxy-image?url=${encodeURIComponent(img)}" onclick="window.open('${img}')">
            </div>
        `).join('');
        
        mediaHtml = `
            <div class="gallery-info">
                <span><i class="fas fa-images"></i> ${data.images.length} ảnh</span>
                <span>Cuộn xem &rarr;</span>
            </div>
            <div class="horizontal-scroll">${imagesHtml}</div>
        `;

        if (isMobile()) {
            buttonsHtml = `
                <button onclick="downloadAllMobile(this)" class="btn-primary" data-images='${JSON.stringify(data.images)}'>
                    <i class="fas fa-layer-group"></i> Tải Tất Cả (Mobile)
                </button>`;
        } else {
            buttonsHtml = `
                <button onclick="downloadZip(this)" class="btn-primary" data-images='${JSON.stringify(data.images)}'>
                    <i class="fas fa-file-archive"></i> Tải File ZIP
                </button>`;
        }
    }

    resultDiv.innerHTML = `
        <div class="user-card">
            <img src="${avatarSrc}" class="avatar" onerror="this.src='https://via.placeholder.com/50'">
            <div class="user-info">
                <div class="username">${data.author}</div>
                <div class="title">${data.title}</div>
            </div>
        </div>
        ${mediaHtml}
        <div class="actions">
            ${buttonsHtml}
            <button onclick="navigator.clipboard.writeText('${originalUrl}')" class="btn-secondary">
                <i class="fas fa-link"></i> Copy Link Gốc
            </button>
        </div>
    `;
    resultDiv.classList.remove('hidden');
}

function showError(msg) {
    document.getElementById('error-msg').classList.remove('hidden');
    document.getElementById('error-msg').querySelector('span').textContent = msg;
}

function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

async function downloadZip(btn) {
    const images = JSON.parse(btn.getAttribute('data-images'));
    const oldText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang nén...'; btn.disabled = true;
    try {
        const res = await fetch('/download-zip', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({images})
        });
        if(res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href=url; a.download=`rednote_album_${Date.now()}.zip`;
            a.click();
        }
    } catch(e) { alert("Lỗi tải"); }
    finally { btn.innerHTML = oldText; btn.disabled = false; }
}

async function downloadAllMobile(btn) {
    const images = JSON.parse(btn.getAttribute('data-images'));
    if(!confirm(`Tải ${images.length} ảnh?`)) return;
    for(let i=0; i<images.length; i++){
        const a = document.createElement('a');
        a.href = `/proxy-download?url=${encodeURIComponent(images[i])}&filename=image_${i+1}.jpg`;
        document.body.appendChild(a); a.click(); a.remove();
        await new Promise(r=>setTimeout(r, 800));
    }
}