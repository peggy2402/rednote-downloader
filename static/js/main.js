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

// --- 1. GLOBAL HELPER FUNCTIONS (QUAN TRỌNG: Phải nằm ở Window Scope) ---

// Hàm cuộn sang trái/phải (Nút mũi tên)
window.scrollGallery = function(galleryId, direction) {
    const gallery = document.getElementById(galleryId);
    if (!gallery) return;

    const item = gallery.querySelector('div'); 
    if (!item) return;
    
    // Width của item + Gap (16px)
    const scrollAmount = (item.offsetWidth + 16) * direction;
    
    gallery.scrollBy({
        left: scrollAmount,
        behavior: 'smooth'
    });
};

// Hàm nhảy đến vị trí cụ thể (Click Dot)
window.scrollToIndex = function(galleryId, index) {
    const gallery = document.getElementById(galleryId);
    if (!gallery) return;
    
    const item = gallery.querySelector('div');
    if (!item) return;
    
    const scrollPos = index * (item.offsetWidth + 16);
    
    gallery.scrollTo({
        left: scrollPos,
        behavior: 'smooth'
    });
};

// Hàm cập nhật chấm tròn khi lướt
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
        if (i === activeIndex) {
            dots[i].classList.add('active');
        } else {
            dots[i].classList.remove('active');
        }
    }
};

// --- 2. LOGIC CHÍNH ---

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
    if (!input.trim()) return alert("Vui lòng nhập link!");

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
            if(actionBar) {
                actionBar.classList.remove('hidden');
                setTimeout(() => actionBar.classList.remove('translate-y-full', 'translate-y-0'), 100);
            }
        } else {
            alert("Lỗi: " + (resData.message || "Không xác định"));
        }
    } catch (error) {
        console.error(error);
        alert("Lỗi kết nối server: " + error.message);
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
                    
                    <!-- Prev Button -->
                    <button class="nav-btn absolute left-2 top-1/2 z-20 bg-white/90 hover:bg-red-500 hover:text-white text-gray-700 w-10 h-10 rounded-full shadow-lg flex items-center justify-center backdrop-blur-sm cursor-pointer transition-transform active:scale-95"
                        onclick="window.scrollGallery('${galleryId}', -1)">
                        <i class="fa-solid fa-chevron-left"></i>
                    </button>

                    <!-- Scroll Area -->
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

                    <!-- Next Button -->
                    <button class="nav-btn absolute right-2 top-1/2 z-20 bg-white/90 hover:bg-red-500 hover:text-white text-gray-700 w-10 h-10 rounded-full shadow-lg flex items-center justify-center backdrop-blur-sm cursor-pointer transition-transform active:scale-95"
                        onclick="window.scrollGallery('${galleryId}', 1)">
                        <i class="fa-solid fa-chevron-right"></i>
                    </button>
                </div>

                <!-- Dots Container -->
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

// 4. Drag & Scroll Logic
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
            a.download = `RedNote_Full_${new Date().getTime()}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } else {
            alert("Lỗi khi tạo ZIP (Có thể file quá lớn).");
        }
    } catch (e) {
        console.error(e);
        alert("Lỗi tải xuống.");
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
        alert("LƯU Ý IOS: Hệ thống sẽ tải lần lượt. Vui lòng nhấn 'Tải về' trên popup.");
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
    setTimeout(() => {
        btn.innerHTML = '<i class="fa-solid fa-images"></i> Tải Tất Cả (Mobile)';
        btn.disabled = false;
    }, 3000);
}