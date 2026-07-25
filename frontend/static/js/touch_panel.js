// Smart Wardrobe - Touch Panel JavaScript
// Touch gestures, swipe navigation, and responsive interactions

(function() {
    'use strict';
    
    // Touch state
    const touchState = {
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        isDragging: false,
        target: null,
        startTime: 0
    };
    
    // Gesture thresholds
    const THRESHOLDS = {
        swipe: 50,        // Minimum distance for swipe
        swipeTime: 300,   // Maximum time for swipe (ms)
        tap: 10,          // Maximum distance for tap
        tapTime: 200,     // Maximum time for tap (ms)
        longPress: 500    // Time for long press (ms)
    };
    
    // Initialize touch panel
    function initTouchPanel() {
        const touchPanel = document.querySelector('.touch-panel');
        if (!touchPanel) return;
        
        // Add touch event listeners
        touchPanel.addEventListener('touchstart', handleTouchStart, { passive: true });
        touchPanel.addEventListener('touchmove', handleTouchMove, { passive: false });
        touchPanel.addEventListener('touchend', handleTouchEnd, { passive: true });
        touchPanel.addEventListener('touchcancel', handleTouchCancel, { passive: true });
        
        // Add pointer events for hybrid devices
        touchPanel.addEventListener('pointerdown', handlePointerDown);
        touchPanel.addEventListener('pointermove', handlePointerMove);
        touchPanel.addEventListener('pointerup', handlePointerUp);
        touchPanel.addEventListener('pointercancel', handlePointerCancel);
        
        // Prevent zoom on double tap
        let lastTouchEnd = 0;
        touchPanel.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, { passive: false });
        
        // Initialize swipe navigation for occasion/season grids
        initSwipeGrids();
        
        // Initialize pull-to-refresh
        initPullToRefresh();
        
        // Initialize haptic feedback
        initHapticFeedback();
    }
    
    // Touch event handlers
    function handleTouchStart(e) {
        const touch = e.touches[0];
        touchState.startX = touch.clientX;
        touchState.startY = touch.clientY;
        touchState.currentX = touch.clientX;
        touchState.currentY = touch.clientY;
        touchState.isDragging = false;
        touchState.target = e.target;
        touchState.startTime = Date.now();
    }
    
    function handleTouchMove(e) {
        if (e.touches.length !== 1) return;
        
        const touch = e.touches[0];
        touchState.currentX = touch.clientX;
        touchState.currentY = touch.clientY;
        
        const deltaX = touchState.currentX - touchState.startX;
        const deltaY = touchState.currentY - touchState.startY;
        
        // Check if dragging
        if (!touchState.isDragging && (Math.abs(deltaX) > THRESHOLDS.tap || Math.abs(deltaY) > THRESHOLDS.tap)) {
            touchState.isDragging = true;
        }
        
        // Handle horizontal swipe on grids
        if (touchState.isDragging && Math.abs(deltaX) > Math.abs(deltaY)) {
            const grid = touchState.target.closest('.occasion-grid, .season-grid, .action-grid');
            if (grid) {
                e.preventDefault();
                handleGridSwipe(grid, deltaX);
            }
        }
        
        // Handle vertical pull-to-refresh
        if (touchState.isDragging && deltaY > 0 && Math.abs(deltaY) > Math.abs(deltaX)) {
            const panel = touchState.target.closest('.touch-panel');
            if (panel && panel.scrollTop === 0) {
                handlePullToRefresh(panel, deltaY);
            }
        }
    }
    
    function handleTouchEnd(e) {
        if (!touchState.isDragging) {
            // Check for tap
            const deltaX = touchState.currentX - touchState.startX;
            const deltaY = touchState.currentY - touchState.startY;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            const duration = Date.now() - touchState.startTime;
            
            if (distance <= THRESHOLDS.tap && duration <= THRESHOLDS.tapTime) {
                handleTap(touchState.target);
            } else if (duration >= THRESHOLDS.longPress && distance <= THRESHOLDS.tap * 2) {
                handleLongPress(touchState.target);
            }
        } else {
            // Handle swipe end
            const deltaX = touchState.currentX - touchState.startX;
            const deltaY = touchState.currentY - touchState.startY;
            const duration = Date.now() - touchState.startTime;
            
            // Horizontal swipe
            if (Math.abs(deltaX) > THRESHOLDS.swipe && duration <= THRESHOLDS.swipeTime) {
                handleSwipe(touchState.target, deltaX > 0 ? 'right' : 'left');
            }
            
            // Vertical swipe (pull to refresh release)
            if (deltaY > THRESHOLDS.swipe && Math.abs(deltaY) > Math.abs(deltaX)) {
                triggerRefresh();
            }
        }
        
        // Reset touch state
        resetTouchState();
    }
    
    function handleTouchCancel(e) {
        resetTouchState();
    }
    
    // Pointer event handlers (for hybrid devices)
    function handlePointerDown(e) {
        if (e.pointerType === 'mouse') return;
        handleTouchStart({ touches: [{ clientX: e.clientX, clientY: e.clientY }], target: e.target });
    }
    
    function handlePointerMove(e) {
        if (e.pointerType === 'mouse') return;
        handleTouchMove({ touches: [{ clientX: e.clientX, clientY: e.clientY }], preventDefault: () => {} });
    }
    
    function handlePointerUp(e) {
        if (e.pointerType === 'mouse') return;
        handleTouchEnd({});
    }
    
    function handlePointerCancel(e) {
        if (e.pointerType === 'mouse') return;
        handleTouchCancel({});
    }
    
    function resetTouchState() {
        touchState.startX = 0;
        touchState.startY = 0;
        touchState.currentX = 0;
        touchState.currentY = 0;
        touchState.isDragging = false;
        touchState.target = null;
        touchState.startTime = 0;
    }
    
    // Grid swipe handling
    function initSwipeGrids() {
        const grids = document.querySelectorAll('.occasion-grid, .season-grid');
        grids.forEach(grid => {
            let isScrolling = false;
            let startX = 0;
            let scrollLeft = 0;
            
            grid.addEventListener('touchstart', (e) => {
                isScrolling = false;
                startX = e.touches[0].clientX;
                scrollLeft = grid.scrollLeft;
            }, { passive: true });
            
            grid.addEventListener('touchmove', (e) => {
                if (!isScrolling) {
                    const deltaX = e.touches[0].clientX - startX;
                    if (Math.abs(deltaX) > THRESHOLDS.tap) {
                        isScrolling = true;
                    }
                }
                
                if (isScrolling) {
                    const deltaX = e.touches[0].clientX - startX;
                    grid.scrollLeft = scrollLeft - deltaX;
                }
            }, { passive: true });
            
            // Snap to items on scroll end
            grid.addEventListener('touchend', () => {
                if (isScrolling) {
                    snapToItem(grid);
                }
            });
        });
    }
    
    function handleGridSwipe(grid, deltaX) {
        // Visual feedback during drag
        grid.style.scrollBehavior = 'auto';
        grid.scrollLeft -= deltaX * 0.5; // Reduced sensitivity during drag
    }
    
    function snapToItem(grid) {
        const items = grid.querySelectorAll('.occasion-btn, .season-btn, .action-btn');
        if (items.length === 0) return;
        
        const itemWidth = items[0].offsetWidth + parseInt(getComputedStyle(grid).gap) || 12;
        const targetScroll = Math.round(grid.scrollLeft / itemWidth) * itemWidth;
        
        grid.style.scrollBehavior = 'smooth';
        grid.scrollLeft = targetScroll;
    }
    
    // Pull to refresh
    function initPullToRefresh() {
        const panel = document.querySelector('.touch-panel');
        if (!panel) return;
        
        let pullIndicator = document.createElement('div');
        pullIndicator.className = 'pull-indicator';
        pullIndicator.innerHTML = `
            <svg class="pull-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M19 12l-7 7-7-7"></path>
            </svg>
            <span class="pull-text">Tira para actualizar</span>
        `;
        pullIndicator.style.cssText = `
            position: absolute;
            top: -60px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            color: var(--text-muted);
            font-size: 0.75rem;
            opacity: 0;
            transition: all 0.2s ease;
            pointer-events: none;
            z-index: 100;
        `;
        panel.style.position = 'relative';
        panel.insertBefore(pullIndicator, panel.firstChild);
    }
    
    function handlePullToRefresh(panel, deltaY) {
        const indicator = panel.querySelector('.pull-indicator');
        if (!indicator) return;
        
        const progress = Math.min(deltaY / 80, 1);
        indicator.style.opacity = progress;
        indicator.style.top = `${-60 + deltaY * 0.5}px`;
        
        const icon = indicator.querySelector('.pull-icon');
        const text = indicator.querySelector('.pull-text');
        
        if (progress >= 1) {
            icon.style.transform = 'rotate(180deg)';
            text.textContent = 'Suelta para actualizar';
        } else {
            icon.style.transform = `rotate(${progress * 180}deg)`;
            text.textContent = 'Tira para actualizar';
        }
    }
    
    function triggerRefresh() {
        const panel = document.querySelector('.touch-panel');
        const indicator = panel?.querySelector('.pull-indicator');
        
        if (indicator) {
            indicator.style.opacity = '0';
            indicator.style.top = '-60px';
            indicator.querySelector('.pull-icon').style.transform = 'rotate(0deg)';
            indicator.querySelector('.pull-text').textContent = 'Tira para actualizar';
        }
        
        // Trigger outfit reload
        if (window.SmartWardrobe && window.SmartWardrobe.loadOutfit) {
            window.SmartWardrobe.loadOutfit();
        }
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([50, 50, 50]);
        }
    }
    
    // Tap handling
    function handleTap(target) {
        // Button press animation
        if (target.matches('.touch-target, .occasion-btn, .season-btn, .action-btn, .feedback-btn')) {
            target.classList.add('pressed');
            setTimeout(() => target.classList.remove('pressed'), 150);
        }
        
        // Haptic feedback for buttons
        if (target.matches('.touch-target')) {
            triggerHaptic('light');
        }
    }
    
    // Long press handling
    function handleLongPress(target) {
        if (target.matches('.wardrobe-item')) {
            // Show context menu for wardrobe items
            showWardrobeContextMenu(target);
        } else if (target.matches('.garment-card')) {
            // Show garment details
            showGarmentDetails(target);
        }
        
        triggerHaptic('medium');
    }
    
    function showWardrobeContextMenu(item) {
        // Create context menu
        const garmentId = item.dataset.garmentId;
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.innerHTML = `
            <button class="context-menu-item" data-action="edit">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                Editar
            </button>
            <button class="context-menu-item" data-action="duplicate">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                Duplicar
            </button>
            <button class="context-menu-item destructive" data-action="delete">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                Eliminar
            </button>
        `;
        
        menu.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-card);
            border: 1px solid var(--border-primary);
            border-radius: var(--radius-lg);
            padding: 8px;
            box-shadow: var(--shadow-xl);
            z-index: 2000;
            display: flex;
            flex-direction: column;
            gap: 4px;
            min-width: 180px;
        `;
        
        // Add styles for menu items
        const style = document.createElement('style');
        style.textContent = `
            .context-menu-item {
                display: flex;
                align-items: center;
                gap: 12px;
                width: 100%;
                padding: 12px 16px;
                background: none;
                border: none;
                border-radius: var(--radius-md);
                color: var(--text-primary);
                font-size: 0.875rem;
                text-align: left;
                cursor: pointer;
                transition: background var(--transition-fast);
            }
            .context-menu-item:hover { background: var(--bg-hover); }
            .context-menu-item.destructive { color: var(--accent-error); }
            .context-menu-item.destructive:hover { background: rgba(239, 68, 68, 0.1); }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(menu);
        
        // Handle clicks
        menu.querySelectorAll('.context-menu-item').forEach(btn => {
            btn.addEventListener('click', async () => {
                const action = btn.dataset.action;
                menu.remove();
                style.remove();
                
                if (action === 'delete') {
                    if (confirm('¿Eliminar esta prenda?')) {
                        try {
                            await window.SmartWardrobe.api(`/garments/${garmentId}`, { method: 'DELETE' });
                            window.SmartWardrobe.showToast('Prenda eliminada', 'success');
                            if (window.SmartWardrobe.loadWardrobe) {
                                window.SmartWardrobe.loadWardrobe();
                            }
                        } catch (error) {
                            window.SmartWardrobe.showToast(`Error: ${error.message}`, 'error');
                        }
                    }
                }
            });
        });
        
        // Close on outside click
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    style.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 0);
    }
    
    function showGarmentDetails(card) {
        // Show garment details in a modal or toast
        const name = card.querySelector('.garment-name')?.textContent || 'Prenda';
        window.SmartWardrobe?.showToast?.(`Detalles de ${name} - próximamente`, 'info');
    }
    
    // Swipe handling for panel navigation
    function handleSwipe(target, direction) {
        // Swipe left/right on visualization panel to change outfit
        const vizPanel = document.querySelector('.visualization-panel');
        if (vizPanel && (target === vizPanel || vizPanel.contains(target))) {
            if (direction === 'left') {
                // Next outfit
                window.SmartWardrobe?.loadOutfit?.();
            } else if (direction === 'right') {
                // Previous outfit - could implement history
                window.SmartWardrobe?.loadOutfit?.();
            }
        }
        
        triggerHaptic('light');
    }
    
    // Haptic feedback
    function initHapticFeedback() {
        if (!navigator.vibrate) return;
        
        // Add haptic to all touch targets
        document.addEventListener('touchstart', (e) => {
            const target = e.target.closest('.touch-target, .occasion-btn, .season-btn, .action-btn, .feedback-btn, .icon-btn, .btn');
            if (target) {
                target.dataset.hapticReady = 'true';
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            const target = e.target.closest('[data-haptic-ready="true"]');
            if (target) {
                delete target.dataset.hapticReady;
                triggerHaptic('light');
            }
        }, { passive: true });
    }
    
    function triggerHaptic(type = 'light') {
        if (!navigator.vibrate) return;
        
        const patterns = {
            light: [10],
            medium: [20],
            heavy: [30],
            selection: [5, 5, 5],
            success: [10, 50, 10],
            error: [30, 30, 30]
        };
        
        navigator.vibrate(patterns[type] || patterns.light);
    }
    
    // Touch-friendly scroll enhancement
    function enhanceScrolling() {
        const scrollableElements = document.querySelectorAll('.wardrobe-grid, .packing-outfits, .touch-content');
        
        scrollableElements.forEach(el => {
            // Momentum scrolling
            el.style.webkitOverflowScrolling = 'touch';
            el.style.overflowY = 'auto';
            
            // Scroll snap for grids
            if (el.classList.contains('wardrobe-grid')) {
                el.style.scrollSnapType = 'y mandatory';
                const items = el.querySelectorAll('.wardrobe-item');
                items.forEach(item => {
                    item.style.scrollSnapAlign = 'start';
                });
            }
        });
    }
    
    // Swipe to dismiss for modals
    function initModalSwipeDismiss() {
        const modals = document.querySelectorAll('.modal');
        
        modals.forEach(modal => {
            const content = modal.querySelector('.modal-content');
            if (!content) return;
            
            let startY = 0;
            let currentY = 0;
            let isDragging = false;
            
            content.addEventListener('touchstart', (e) => {
                startY = e.touches[0].clientY;
                isDragging = true;
            }, { passive: true });
            
            content.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                
                currentY = e.touches[0].clientY;
                const deltaY = currentY - startY;
                
                if (deltaY > 0) {
                    content.style.transform = `translateY(${deltaY * 0.5}px)`;
                    content.style.transition = 'none';
                    
                    // Fade overlay
                    const overlay = modal.querySelector('.modal-overlay');
                    if (overlay) {
                        overlay.style.opacity = Math.max(0, 1 - deltaY / 300);
                    }
                }
            }, { passive: true });
            
            content.addEventListener('touchend', () => {
                if (!isDragging) return;
                isDragging = false;
                
                const deltaY = currentY - startY;
                
                if (deltaY > 100) {
                    // Dismiss modal
                    content.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
                    content.style.transform = 'translateY(100%)';
                    content.style.opacity = '0';
                    
                    setTimeout(() => {
                        if (window.SmartWardrobe) {
                            window.SmartWardrobe.closeModal(modal);
                        }
                        content.style.transform = '';
                        content.style.opacity = '';
                    }, 300);
                } else {
                    // Snap back
                    content.style.transition = 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    content.style.transform = '';
                    
                    const overlay = modal.querySelector('.modal-overlay');
                    if (overlay) {
                        overlay.style.opacity = '';
                    }
                }
                
                currentY = 0;
            }, { passive: true });
        });
    }
    
    // Keyboard navigation support
    function initKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Arrow keys for occasion/season grids
            if (e.target.matches('.occasion-btn, .season-btn')) {
                const grid = e.target.closest('.occasion-grid, .season-grid');
                const buttons = Array.from(grid.querySelectorAll('.occasion-btn, .season-btn'));
                const index = buttons.indexOf(e.target);
                
                let newIndex = index;
                if (e.key === 'ArrowRight') newIndex = (index + 1) % buttons.length;
                if (e.key === 'ArrowLeft') newIndex = (index - 1 + buttons.length) % buttons.length;
                
                if (newIndex !== index) {
                    e.preventDefault();
                    buttons[newIndex].focus();
                    buttons[newIndex].click();
                }
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
                    if (window.SmartWardrobe) {
                        window.SmartWardrobe.closeModal(modal);
                    }
                });
            }
            
            // Enter/Space on touch targets
            if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.touch-target')) {
                e.preventDefault();
                e.target.click();
            }
        });
    }
    
    // Responsive layout adjustments
    function handleResize() {
        const isMobile = window.innerWidth < 768;
        const touchPanel = document.querySelector('.touch-panel');
        
        if (touchPanel) {
            if (isMobile) {
                touchPanel.classList.add('mobile');
            } else {
                touchPanel.classList.remove('mobile', 'expanded');
                touchPanel.style.transform = '';
            }
        }
    }
    
    // Initialize everything
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                initTouchPanel();
                enhanceScrolling();
                initModalSwipeDismiss();
                initKeyboardNavigation();
                handleResize();
                window.addEventListener('resize', handleResize);
            });
        } else {
            initTouchPanel();
            enhanceScrolling();
            initModalSwipeDismiss();
            initKeyboardNavigation();
            handleResize();
            window.addEventListener('resize', handleResize);
        }
    }
    
    // Expose haptic function globally
    window.triggerHaptic = triggerHaptic;
    
    // Auto-initialize
    init();
    
})();