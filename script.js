// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            const offsetTop = target.offsetTop - 80;
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    });
});

// Intersection Observer for scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            // Add delay based on data-delay attribute
            const delay = entry.target.getAttribute('data-delay');
            if (delay) {
                entry.target.style.transitionDelay = `${delay}ms`;
            }
        }
    });
}, observerOptions);

// Observe all animated elements
document.querySelectorAll('.fade-in-up, .fade-in-left, .fade-in-right').forEach(el => {
    observer.observe(el);
});

// Navbar scroll effect
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
        navbar.style.background = 'rgba(10, 10, 15, 0.95)';
        navbar.style.boxShadow = '0 4px 20px rgba(0, 217, 255, 0.1)';
    } else {
        navbar.style.background = 'rgba(10, 10, 15, 0.8)';
        navbar.style.boxShadow = 'none';
    }
    
    lastScroll = currentScroll;
});

// Mobile menu toggle
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const navLinks = document.querySelector('.nav-links');

if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
        mobileMenuToggle.classList.toggle('active');
    });
}

// Parallax effect for hero background
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero-background');
    if (hero) {
        hero.style.transform = `translateY(${scrolled * 0.5}px)`;
    }
});

// Animate numbers/counters (if needed in future)
function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        element.textContent = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Add hover effects to cards
document.querySelectorAll('.benefit-card, .problem-card, .service-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-8px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// Add ripple effect to buttons
document.querySelectorAll('.btn-primary, .btn-secondary').forEach(button => {
    button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        this.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    });
});

// Add CSS for ripple effect
const style = document.createElement('style');
style.textContent = `
    .btn-primary, .btn-secondary {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    @media (max-width: 767px) {
        .nav-links {
            position: fixed;
            top: 70px;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            flex-direction: column;
            padding: var(--spacing-lg);
            border-top: 1px solid rgba(0, 217, 255, 0.1);
            transform: translateY(-100%);
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }
        
        .nav-links.active {
            transform: translateY(0);
            opacity: 1;
            visibility: visible;
        }
        
        .mobile-menu-toggle.active span:nth-child(1) {
            transform: rotate(45deg) translate(5px, 5px);
        }
        
        .mobile-menu-toggle.active span:nth-child(2) {
            opacity: 0;
        }
        
        .mobile-menu-toggle.active span:nth-child(3) {
            transform: rotate(-45deg) translate(7px, -6px);
        }
    }
`;
document.head.appendChild(style);

// Lazy load images (if added in future)
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// Add typing effect to hero subtitle (optional enhancement)
function typeWriter(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// Performance optimization: throttle scroll events
function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Apply throttling to scroll handlers
const throttledScroll = throttle(() => {
    // Scroll-based animations can be added here
}, 16);

window.addEventListener('scroll', throttledScroll);

// Initialize Yandex Map
function initMap() {
    if (typeof ymaps === 'undefined') {
        console.warn('Yandex Maps API not loaded');
        // Показываем fallback, если карта не загрузилась
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            mapContainer.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #a0a0b0;">Карта загружается...</div>';
        }
        return;
    }

    ymaps.ready(function () {
        const mapContainer = document.getElementById('map');
        if (!mapContainer) {
            console.warn('Map container not found');
            return;
        }
        // Центр карты - Нижневартовск
        const map = new ymaps.Map('map', {
            center: [60.9394, 76.5694], // Нижневартовск
            zoom: 12,
            controls: ['zoomControl', 'fullscreenControl']
        });

        // Стиль карты - тёмная тема
        map.options.set('theme', 'dark');

        // Точки станций в спальных районах Нижневартовска (2026)
        const stations = [
            {
                coords: [60.9450, 76.5750],
                name: 'Станция №1',
                address: 'ул. Ленина, 15',
                status: 'Работает 24/7',
                available: true
            },
            {
                coords: [60.9300, 76.5600],
                name: 'Станция №2',
                address: 'пр. Победы, 8',
                status: 'Работает 24/7',
                available: true
            },
            {
                coords: [60.9500, 76.5800],
                name: 'Станция №3',
                address: 'ул. Мира, 25',
                status: 'Работает 24/7',
                available: true
            },
            {
                coords: [60.9200, 76.5500],
                name: 'Станция №4',
                address: 'ул. Ханты-Мансийская, 12',
                status: 'Откроется в Q2 2026',
                available: false
            },
            {
                coords: [60.9550, 76.5850],
                name: 'Станция №5',
                address: 'пр. Комсомольский, 30',
                status: 'Откроется в Q2 2026',
                available: false
            }
        ];

        // Создаём кастомные иконки для маркеров
        const createCustomIcon = (isAvailable = true) => {
            const strokeColor = isAvailable ? '#00FF88' : '#FFA500';
            const fillColor = isAvailable ? '#00FF88' : '#FFA500';
            const svg = `
                <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="20" cy="20" r="18" fill="#0a0a0f" stroke="${strokeColor}" stroke-width="2"/>
                    <circle cx="20" cy="20" r="8" fill="${fillColor}"/>
                    <circle cx="20" cy="20" r="4" fill="#0a0a0f"/>
                </svg>
            `;
            return 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg)));
        };

        stations.forEach((station) => {
            const statusColor = station.available ? '#00FF88' : '#FFA500';
            const statusIcon = station.available ? '✓' : '⏳';
            
            const placemark = new ymaps.Placemark(station.coords, {
                balloonContentHeader: `<strong style="color: #00D9FF;">${station.name}</strong>`,
                balloonContentBody: `<p style="color: #ffffff; margin: 8px 0;">${station.address}</p><p style="color: ${statusColor}; margin: 8px 0;">${statusIcon} ${station.status}</p>`,
                balloonContentFooter: '<a href="#bot" style="color: #00D9FF; text-decoration: none;">Узнать больше →</a>',
                hintContent: station.name
            }, {
                iconLayout: 'default#imageWithContent',
                iconImageHref: createCustomIcon(station.available),
                iconImageSize: [40, 40],
                iconImageOffset: [-20, -20],
                iconShape: {
                    type: 'Circle',
                    coordinates: [0, 0],
                    radius: 20
                }
            });

            map.geoObjects.add(placemark);
        });

        // Устанавливаем границы карты, чтобы все точки были видны
        if (stations.length > 0) {
            map.setBounds(map.geoObjects.getBounds(), {
                checkZoomRange: true,
                duration: 500
            });
        }

        // Применяем тёмную тему к элементам управления
        setTimeout(() => {
            const controls = document.querySelectorAll('[class*="ymaps-2-"][class*="-controls"]');
            controls.forEach(control => {
                control.style.filter = 'brightness(0.8) contrast(1.2)';
            });
        }, 1000);
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    console.log('VoltStation website loaded');
    
    // Инициализируем карту после загрузки Яндекс.Карт
    if (typeof ymaps !== 'undefined') {
        initMap();
    } else {
        // Если API ещё не загружен, ждём его
        window.addEventListener('load', () => {
            if (typeof ymaps !== 'undefined') {
                initMap();
            }
        });
    }
});

// Add smooth reveal animation for sections
const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
});

// Observe all sections
document.querySelectorAll('section').forEach(section => {
    sectionObserver.observe(section);
});
