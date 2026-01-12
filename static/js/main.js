let collectedFiles = []; 

document.addEventListener('DOMContentLoaded', () => {
    console.log("Main JS Loaded");
    detectDevice();
    window.addEventListener('resize', detectDevice);

    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeUrls);
    }

    const btnZip = document.getElementById('btn-download-zip');
    if (btnZip) btnZip.addEventListener('click', downloadZip);

    const btnMobile = document.getElementById('btn-download-mobile');
    if (btnMobile) btnMobile.addEventListener('click', downloadMobileAll);
});

// --- 1. HÀM ALERT ĐẸP (TOAST NOTIFICATION) ---
window.showToast = function(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // Cấu hình màu sắc và icon dựa trên loại thông báo
    const config = {
        success: { bg: 'bg-green-500', icon: '<i class="fa-solid fa-check-circle"></i>', border: 'border-green-600' },
        error: { bg: 'bg-red-500', icon: '<i class="fa-solid fa-circle-exclamation"></i>', border: 'border-red-600' },
        info: { bg: 'bg-blue-500', icon: '<i class="fa-solid fa-circle-info"></i>', border: 'border-blue-600' },
        warning: { bg: 'bg-yellow-500', icon: '<i class="fa-solid fa-triangle-exclamation"></i>', border: 'border-yellow-600' }
    };

    const style = config[type] || config.info;

    // Tạo phần tử Toast HTML
    const toast = document.createElement('div');
    toast.className = `toast-enter pointer-events-auto flex items-center w-full p-4 text-white rounded-xl shadow-2xl ${style.bg} border-b-4 ${style.border} relative overflow-hidden group`;
    
    toast.innerHTML = `
        <div class="flex-shrink-0 text-xl opacity-90">
            ${style.icon}
        </div>
        <div class="ml-3 font-medium text-sm pr-6 leading-tight">
            ${message}
        </div>
        <button onclick="this.parentElement.remove()" class="absolute top-2 right-2 text-white/60 hover:text-white transition p-1">
            <i class="fa-solid fa-xmark"></i>
        </button>
        <!-- Thanh thời gian tự chạy -->
        <div class="absolute bottom-0 left-0 h-1 bg-white/30 animate-[width_3s_linear_forwards]" style="width: 100%"></div>
    `;

    container.appendChild(toast);

    // Tự động xóa sau 3.5 giây
    setTimeout(() => {
        toast.classList.remove('toast-enter');
        toast.classList.add('toast-exit');
        toast.addEventListener('animationend', () => {
            if (toast.parentElement) toast.remove();
        });
    }, 3500);
};

// --- 2. GLOBAL HELPER FUNCTIONS ---

window.scrollGallery = function(galleryId, direction) {
    const gallery = document.getElementById(galleryId);
    if (!gallery) return;
    const item = gallery.querySelector('div'); 
    if (!item) return;
    const scrollAmount = (item.offsetWidth + 16) * direction;
    gallery.scrollBy({ left: scrollAmount, behavior: 'smooth' });
};

window.scrollToIndex = function(galleryId, index) {
    const gallery = document.getElementById(galleryId);
    if (!gallery) return;
    const item = gallery.querySelector('div');
    if (!item) return;
    const scrollPos = index * (item.offsetWidth + 16);
    gallery.scrollTo({ left: scrollPos, behavior: 'smooth' });
};

window.updateActiveDot = function(galleryId, dotsId) {
    const gallery = document.getElementById(galleryId);
    const dotsContainer = document.getElementById(dotsId);
    if (!gallery || !dotsContainer) return;
    const item = gallery.querySelector('div');
    if (!item) return;
    const itemWidth = item.offsetWidth + 16;
    const scrollLeft = gallery.scrollLeft;
    const activeIndex = Math.round(scrollLeft / itemWidth);
    const dots = dotsContainer.children;
    for (let i = 0; i < dots.length; i++) {
        if (i === activeIndex) dots[i].classList.add('active');
        else dots[i].classList.remove('active');
    }
};

// --- 3. LOGIC CHÍNH ---

function detectDevice() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
    const indicator = document.getElementById('device-indicator');
    const btnZip = document.getElementById('btn-download-zip');
    const btnMobile = document.getElementById('btn-download-mobile');

    if (!indicator) return;

    if (isMobile) {
        indicator.textContent = "Mobile Mode";
        indicator.className = "text-xs px-3 py-1 rounded-full bg-red-100 text-red-600 font-bold";
        if(btnZip) btnZip.classList.add('hidden');
        if(btnMobile) btnMobile.classList.remove('hidden');
    } else {
        indicator.textContent = "PC Mode";
        indicator.className = "text-xs px-3 py-1 rounded-full bg-blue-100 text-blue-600 font-bold";
        if(btnZip) btnZip.classList.remove('hidden');
        if(btnMobile) btnMobile.classList.add('hidden');
    }
}

async function analyzeUrls() {
    const input = document.getElementById('url-input').value;
    if (!input.trim()) {
        showToast("Vui lòng dán link Xiaohongshu!", "warning");
        return;
    }

    collectedFiles = [];
    const resultsArea = document.getElementById('results-area');
    const actionBar = document.getElementById('action-bar');
    const loader = document.getElementById('loading');
    
    resultsArea.innerHTML = '';
    resultsArea.classList.add('hidden');
    if(actionBar) actionBar.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: input })
        });
        
        const resData = await response.json();

        if (resData.success) {
            renderResults(resData.data);
            showToast(`Đã tìm thấy ${resData.data.length} bài viết!`, "success");
            
            if(resData.debug_errors && resData.debug_errors.length > 0) {
                // Nếu có 1 số link lỗi nhưng vẫn có kết quả trả về
                setTimeout(() => {
                    showToast(`Có ${resData.debug_errors.length} link không tải được.`, "warning");
                }, 1000);
            }

            if(actionBar) {
                actionBar.classList.remove('hidden');
                setTimeout(() => actionBar.classList.remove('translate-y-full', 'translate-y-0'), 100);
            }
        } else {
            showToast("Lỗi: " + (resData.message || "Không xác định"), "error");
        }
    } catch (error) {
        console.error(error);
        showToast("Lỗi kết nối Server!", "error");
    } finally {
        loader.classList.add('hidden');
    }
}

function renderResults(posts) {
    const container = document.getElementById('results-area');
    
    posts.forEach(post => {
        collectedFiles.push(...post.files);
        const galleryId = `gallery-${post.id}`;
        const dotsId = `dots-${post.id}`;

        const html = `
            <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden group hover:shadow-lg transition duration-300 pb-4">
                <!-- Header -->
                <div class="p-4 border-b border-gray-50 flex items-center justify-between bg-white z-10 relative">
                    <div class="flex items-center gap-3 overflow-hidden">
                        <img src="${post.author.avatar}" referrerpolicy="no-referrer" class="w-10 h-10 rounded-full bg-gray-100 object-cover border border-gray-200 select-none">
                        <div class="min-w-0">
                            <h3 class="font-bold text-gray-800 truncate pr-2 select-none text-base">${post.title}</h3>
                            <p class="text-xs text-gray-500 truncate flex items-center gap-1 select-none">
                                <i class="fa-regular fa-user"></i> ${post.author.name}
                            </p>
                        </div>
                    </div>
                    <span class="text-xs font-bold text-red-500 bg-red-50 px-3 py-1 rounded-full border border-red-100 whitespace-nowrap select-none">
                        ${post.total} items
                    </span>
                </div>

                <!-- Carousel Wrapper -->
                <div class="relative bg-gray-50 group/slider pt-4">
                    <button class="nav-btn absolute left-2 top-1/2 z-20 bg-white/90 hover:bg-red-500 hover:text-white text-gray-700 w-10 h-10 rounded-full shadow-lg flex items-center justify-center backdrop-blur-sm cursor-pointer transition-transform active:scale-95"
                        onclick="window.scrollGallery('${galleryId}', -1)">
                        <i class="fa-solid fa-chevron-left"></i>
                    </button>

                    <div id="${galleryId}" class="xhs-gallery-scroll flex overflow-x-auto snap-x snap-mandatory scroll-smooth p-4 gap-4 scrollbar-hide cursor-grab active:cursor-grabbing items-center"
                         onscroll="window.updateActiveDot('${galleryId}', '${dotsId}')">
                        ${post.files.map((file, index) => `
                            <div class="snap-center shrink-0 w-[85vw] md:w-80 aspect-[3/4] relative rounded-2xl overflow-hidden bg-white shadow-sm border border-gray-100 group/item transition-transform">
                                ${file.type === 'video' 
                                    ? `<video controls class="w-full h-full object-contain bg-black pointer-events-auto" poster="${file.cover || ''}" preload="metadata" referrerpolicy="no-referrer">
                                         <source src="${file.url}" type="video/mp4">
                                       </video>`
                                    : `<img src="${file.url}" draggable="false" referrerpolicy="no-referrer" class="w-full h-full object-cover pointer-events-none">`
                                }
                                <div class="absolute inset-0 bg-black/0 group-hover/item:bg-black/10 transition-colors pointer-events-none"></div>
                                <a href="${file.url}" download="${file.filename}" target="_blank" 
                                   class="absolute top-3 right-3 bg-white/90 hover:bg-red-500 hover:text-white text-gray-700 w-9 h-9 flex items-center justify-center rounded-full shadow-md backdrop-blur-md transition-all opacity-0 group-hover/item:opacity-100 translate-y-2 group-hover/item:translate-y-0 z-10 cursor-pointer"
                                   title="Tải về">
                                    <i class="fa-solid fa-download"></i>
                                </a>
                                <div class="absolute bottom-3 left-3 bg-black/60 text-white text-[10px] font-bold px-2 py-1 rounded backdrop-blur-sm pointer-events-none">
                                    ${index + 1} / ${post.total}
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <button class="nav-btn absolute right-2 top-1/2 z-20 bg-white/90 hover:bg-red-500 hover:text-white text-gray-700 w-10 h-10 rounded-full shadow-lg flex items-center justify-center backdrop-blur-sm cursor-pointer transition-transform active:scale-95"
                        onclick="window.scrollGallery('${galleryId}', 1)">
                        <i class="fa-solid fa-chevron-right"></i>
                    </button>
                </div>

                <div id="${dotsId}" class="dots-container">
                    ${post.files.map((_, index) => `
                        <div class="dot ${index === 0 ? 'active' : ''}" onclick="window.scrollToIndex('${galleryId}', ${index})"></div>
                    `).join('')}
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', html);
    });

    attachDragAndScroll();
    container.classList.remove('hidden');
}

function attachDragAndScroll() {
    const galleries = document.querySelectorAll('.xhs-gallery-scroll');
    galleries.forEach(slider => {
        let isDown = false;
        let startX;
        let scrollLeft;
        slider.addEventListener('mousedown', (e) => {
            isDown = true;
            slider.style.cursor = 'grabbing';
            slider.style.scrollBehavior = 'auto'; 
            slider.style.scrollSnapType = 'none'; 
            startX = e.pageX - slider.offsetLeft;
            scrollLeft = slider.scrollLeft;
            e.preventDefault(); 
        });
        const stopDrag = () => {
            if (!isDown) return;
            isDown = false;
            slider.style.cursor = 'grab';
            slider.style.scrollBehavior = 'smooth';
            slider.style.scrollSnapType = 'x mandatory'; 
        };
        slider.addEventListener('mouseleave', stopDrag);
        slider.addEventListener('mouseup', stopDrag);
        slider.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - slider.offsetLeft;
            const walk = (x - startX) * 2; 
            slider.scrollLeft = scrollLeft - walk;
        });
        slider.addEventListener('wheel', (evt) => {
            if (evt.deltaY !== 0) {
                evt.preventDefault();
                slider.scrollLeft += evt.deltaY;
            }
        });
    });
}

// 5. Download ZIP (Video + Photo)
async function downloadZip() {
    if (collectedFiles.length === 0) return;
    const btn = document.getElementById('btn-download-zip');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nén Server...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/download-zip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: collectedFiles })
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `XHS_Chien_Full_${new Date().getTime()}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showToast("Đã tạo file ZIP thành công!", "success");
        } else {
            showToast("Lỗi khi tạo file ZIP (File quá lớn?).", "error");
        }
    } catch (e) {
        console.error(e);
        showToast("Lỗi kết nối khi tải xuống.", "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// 6. Download Mobile Proxy
async function downloadMobileAll() {
    if (collectedFiles.length === 0) return;
    const btn = document.getElementById('btn-download-mobile');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải...';

    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    
    if (isIOS) {
        showToast("iOS: Vui lòng xác nhận từng popup tải về!", "info");
    } else {
        showToast("Đang bắt đầu tải xuống hàng loạt...", "info");
    }

    for (let i = 0; i < collectedFiles.length; i++) {
        const file = collectedFiles[i];
        const proxyUrl = `/api/proxy?url=${encodeURIComponent(file.url)}&filename=${file.filename}`;
        
        try {
            const a = document.createElement('a');
            a.href = proxyUrl;
            a.download = file.filename;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            await new Promise(r => setTimeout(r, 1500)); 
        } catch (e) {
            console.error("Lỗi tải:", e);
        }
    }

    btn.innerHTML = '<i class="fa-solid fa-check"></i> Hoàn tất';
    showToast("Đã hoàn tất quá trình tải xuống!", "success");
    
    setTimeout(() => {
        btn.innerHTML = '<i class="fa-solid fa-images"></i> Tải Tất Cả (Mobile)';
        btn.disabled = false;
    }, 3000);
}