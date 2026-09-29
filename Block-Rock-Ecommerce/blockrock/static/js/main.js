/**
 * INGOT Lifestyle Apparel & Gear — Core Storefront Scripts
 * Vanilla JS, accessible, zero external dependencies.
 */

document.addEventListener('DOMContentLoaded', () => {
  initToasts();
  initHeaderNavigation();
  initSearchAutocomplete();
  initHeroCarousel();
  initListingFiltersDrawer();
  initWishlistToggles();
  initPDPGallery();
  initPDPVariantsAndCart();
  initSizeChartModal();
  initStickyMobileCart();
});

/* ==========================================================================
   Toast Notification System
   ========================================================================== */
function showToast(message, type = 'info') {
  let container = document.querySelector('.messages');
  if (!container) {
    container = document.createElement('div');
    container.className = 'container messages';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `message ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function initToasts() {
  const existing = document.querySelectorAll('.messages .message');
  existing.forEach(toast => {
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'opacity 0.3s, transform 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  });
}

/* ==========================================================================
   Header Navigation & Account Dropdown
   ========================================================================== */
function initHeaderNavigation() {
  const accountBtn = document.getElementById('account-dropdown-btn');
  const accountDropdown = document.getElementById('account-menu-dropdown');
  const accountWrap = document.getElementById('account-dropdown-wrap');

  if (accountBtn && accountDropdown) {
    accountBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = accountDropdown.classList.toggle('open');
      accountBtn.setAttribute('aria-expanded', String(isOpen));
    });

    document.addEventListener('click', (e) => {
      if (accountWrap && !accountWrap.contains(e.target)) {
        accountDropdown.classList.remove('open');
        accountBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Mobile navigation toggle
  const menuToggle = document.getElementById('mobile-menu-toggle');
  const primaryNav = document.getElementById('primary-nav');
  if (menuToggle && primaryNav) {
    menuToggle.addEventListener('click', () => {
      const open = primaryNav.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.classList.toggle('active', open);
    });
  }
}

/* ==========================================================================
   Search Autocomplete
   ========================================================================== */
function initSearchAutocomplete() {
  const searchInput = document.getElementById('nav-search-input');
  const dropdown = document.getElementById('search-autocomplete-dropdown');
  if (!searchInput || !dropdown) return;

  let debounceTimer;

  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) {
      dropdown.style.display = 'none';
      dropdown.innerHTML = '';
      return;
    }

    debounceTimer = setTimeout(() => {
      fetch(`/products/api/search-autocomplete/?q=${encodeURIComponent(q)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(res => res.json())
      .then(data => {
        if (!data.results || data.results.length === 0) {
          dropdown.innerHTML = `
            <div class="autocomplete-empty">
              <span>No products matching "<strong>${escapeHtml(q)}</strong>"</span>
            </div>
          `;
          dropdown.style.display = 'block';
          return;
        }

        dropdown.innerHTML = `
          <div class="autocomplete-header">PRODUCTS &amp; CATEGORIES</div>
          ${data.results.map(item => `
            <a href="/products/${item.slug}/" class="autocomplete-item">
              ${item.image_url ? `<img src="${item.image_url}" alt="" class="ac-img">` : `<div class="ac-placeholder">✦</div>`}
              <div class="ac-info">
                <span class="ac-name">${escapeHtml(item.name)}</span>
                <span class="ac-meta">${escapeHtml(item.category)} &bull; ${escapeHtml(item.collection)}</span>
              </div>
              <strong class="ac-price">${item.price}</strong>
            </a>
          `).join('')}
          <div class="autocomplete-footer">
            <button type="submit" form="nav-search-form" class="ac-view-all">View all results for "${escapeHtml(q)}" &rarr;</button>
          </div>
        `;
        dropdown.style.display = 'block';
      })
      .catch(() => {
        dropdown.style.display = 'none';
      });
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });
}

function escapeHtml(str) {
  return String(str || '').replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

/* ==========================================================================
   Hero Carousel (Auto-rotating, Pause on Hover, Prev/Next, Dots)
   ========================================================================== */
function initHeroCarousel() {
  const carousel = document.getElementById('hero-carousel');
  if (!carousel) return;

  const slides = carousel.querySelectorAll('.carousel-slide');
  const dots = carousel.querySelectorAll('.carousel-dot');
  const prevBtn = document.getElementById('carousel-prev');
  const nextBtn = document.getElementById('carousel-next');
  if (slides.length <= 1) return;

  let currentIndex = 0;
  let autoplayInterval;
  const autoplayDuration = parseInt(carousel.dataset.autoplay || '5000', 10);

  function goToSlide(index) {
    slides[currentIndex].classList.remove('active');
    if (dots[currentIndex]) dots[currentIndex].classList.remove('active');

    currentIndex = (index + slides.length) % slides.length;

    slides[currentIndex].classList.add('active');
    if (dots[currentIndex]) dots[currentIndex].classList.add('active');
  }

  function startAutoplay() {
    stopAutoplay();
    autoplayInterval = setInterval(() => {
      goToSlide(currentIndex + 1);
    }, autoplayDuration);
  }

  function stopAutoplay() {
    if (autoplayInterval) clearInterval(autoplayInterval);
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      goToSlide(currentIndex - 1);
      startAutoplay();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      goToSlide(currentIndex + 1);
      startAutoplay();
    });
  }

  dots.forEach(dot => {
    dot.addEventListener('click', () => {
      const idx = parseInt(dot.dataset.index, 10);
      goToSlide(idx);
      startAutoplay();
    });
  });

  carousel.addEventListener('mouseenter', stopAutoplay);
  carousel.addEventListener('mouseleave', startAutoplay);

  startAutoplay();
}

/* ==========================================================================
   Listing Page: Mobile Filter Drawer
   ========================================================================== */
function initListingFiltersDrawer() {
  const openBtn = document.getElementById('mobile-filter-open-btn');
  const closeBtn = document.getElementById('drawer-close-btn');
  const drawer = document.getElementById('listing-sidebar-drawer');
  const backdrop = document.getElementById('sidebar-drawer-backdrop');

  if (!drawer) return;

  function openDrawer() {
    drawer.classList.add('drawer-open');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    drawer.classList.remove('drawer-open');
    document.body.style.overflow = '';
  }

  if (openBtn) openBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);
}

/* ==========================================================================
   Wishlist Heart Toggle (AJAX)
   ========================================================================== */
function initWishlistToggles() {
  document.querySelectorAll('.card-wishlist-overlay-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('.card-heart-btn');
      const actionUrl = form.action;
      const formData = new FormData(form);

      fetch(actionUrl, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json, text/html'
        }
      })
      .then(res => {
        if (res.ok) {
          const wasSaved = btn.classList.contains('saved');
          btn.classList.toggle('saved', !wasSaved);
          const svgPath = btn.querySelector('svg');
          if (svgPath) svgPath.setAttribute('fill', wasSaved ? 'none' : 'currentColor');

          // Update header count badge
          const badge = document.querySelector('.wishlist-count-badge');
          if (badge) {
            let current = parseInt(badge.textContent || '0', 10);
            current = wasSaved ? Math.max(0, current - 1) : current + 1;
            badge.textContent = current;
            badge.style.display = current > 0 ? 'inline-flex' : 'none';
          }

          showToast(wasSaved ? 'Item removed from your wishlist.' : 'Item saved to your wishlist!', 'success');
        } else {
          form.submit();
        }
      })
      .catch(() => form.submit());
    });
  });
}

/* ==========================================================================
   PDP Gallery: Magnifier Loupe & Fullscreen Lightbox
   ========================================================================== */
function initPDPGallery() {
  const mainStage = document.getElementById('gallery-main-stage');
  const mainViewport = document.getElementById('main-image-viewport');
  const mainImg = document.getElementById('main-display-image');
  const magnifierLens = document.getElementById('pdp-magnifier-lens');
  const thumbBtns = document.querySelectorAll('.gallery-thumb-btn');
  const prevArrow = document.getElementById('gallery-prev-arrow');
  const nextArrow = document.getElementById('gallery-next-arrow');

  if (!mainViewport || !mainImg) return;

  // Read images list
  let images = [];
  const scriptImages = document.getElementById('gallery-images-json');
  if (scriptImages) {
    try {
      images = JSON.parse(scriptImages.textContent);
    } catch(e) {}
  }

  let activeIndex = 0;

  function setActiveImage(index) {
    if (images.length === 0) return;
    activeIndex = (index + images.length) % images.length;
    const imgData = images[activeIndex];

    mainImg.src = imgData.src;
    mainImg.alt = imgData.alt || '';
    mainImg.dataset.zoom = imgData.src;

    thumbBtns.forEach((btn, i) => {
      btn.classList.toggle('active', i === activeIndex);
    });

    const mobileDots = document.querySelectorAll('.mobile-gallery-dots .mobile-dot');
    mobileDots.forEach((dot, i) => {
      dot.classList.toggle('active', i === activeIndex);
    });
  }

  thumbBtns.forEach((btn, idx) => {
    btn.addEventListener('click', () => setActiveImage(idx));
  });

  if (prevArrow) {
    prevArrow.addEventListener('click', () => setActiveImage(activeIndex - 1));
  }
  if (nextArrow) {
    nextArrow.addEventListener('click', () => setActiveImage(activeIndex + 1));
  }

  // --- Circular Magnifier Loupe (Desktop Hover) ---
  if (magnifierLens && window.matchMedia('(hover: hover) and (min-width: 900px)').matches) {
    mainViewport.addEventListener('mouseenter', () => {
      magnifierLens.style.display = 'block';
      magnifierLens.style.backgroundImage = `url('${mainImg.dataset.zoom || mainImg.src}')`;
      const rect = mainViewport.getBoundingClientRect();
      magnifierLens.style.backgroundSize = `${rect.width * 2.2}px ${rect.height * 2.2}px`;
    });

    mainViewport.addEventListener('mousemove', (e) => {
      const rect = mainViewport.getBoundingClientRect();
      const lensWidth = magnifierLens.offsetWidth || 130;
      const lensHeight = magnifierLens.offsetHeight || 130;

      let x = e.clientX - rect.left;
      let y = e.clientY - rect.top;

      // Keep lens inside viewport
      x = Math.max(lensWidth / 2, Math.min(x, rect.width - lensWidth / 2));
      y = Math.max(lensHeight / 2, Math.min(y, rect.height - lensHeight / 2));

      magnifierLens.style.left = `${x - lensWidth / 2}px`;
      magnifierLens.style.top = `${y - lensHeight / 2}px`;

      const bgX = ((x / rect.width) * 100);
      const bgY = ((y / rect.height) * 100);
      magnifierLens.style.backgroundPosition = `${bgX}% ${bgY}%`;
    });

    mainViewport.addEventListener('mouseleave', () => {
      magnifierLens.style.display = 'none';
    });
  }

  // --- Fullscreen Lightbox / Filmstrip View ---
  const lightboxModal = document.getElementById('fullscreen-lightbox-modal');
  const lightboxActiveImg = document.getElementById('lightbox-active-img');
  const lightboxCloseBtn = document.getElementById('lightbox-close-btn');
  const lightboxBackdrop = document.getElementById('lightbox-backdrop');
  const lightboxPrevBtn = document.getElementById('lightbox-prev-btn');
  const lightboxNextBtn = document.getElementById('lightbox-next-btn');
  const filmstripThumbs = document.querySelectorAll('.filmstrip-thumb');

  function openLightbox(index) {
    if (!lightboxModal || images.length === 0) return;
    lightboxModal.classList.add('open');
    lightboxModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setLightboxIndex(index);
  }

  function closeLightbox() {
    if (!lightboxModal) return;
    lightboxModal.classList.remove('open');
    lightboxModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function setLightboxIndex(idx) {
    if (images.length === 0) return;
    activeIndex = (idx + images.length) % images.length;
    const imgData = images[activeIndex];
    if (lightboxActiveImg) {
      lightboxActiveImg.src = imgData.src;
      lightboxActiveImg.alt = imgData.alt || '';
    }
    filmstripThumbs.forEach((btn, i) => {
      btn.classList.toggle('active', i === activeIndex);
    });
    // sync main stage
    setActiveImage(activeIndex);
  }

  mainViewport.addEventListener('click', () => {
    openLightbox(activeIndex);
  });

  if (lightboxCloseBtn) lightboxCloseBtn.addEventListener('click', closeLightbox);
  if (lightboxBackdrop) lightboxBackdrop.addEventListener('click', closeLightbox);

  if (lightboxPrevBtn) {
    lightboxPrevBtn.addEventListener('click', () => setLightboxIndex(activeIndex - 1));
  }
  if (lightboxNextBtn) {
    lightboxNextBtn.addEventListener('click', () => setLightboxIndex(activeIndex + 1));
  }

  filmstripThumbs.forEach((thumb, idx) => {
    thumb.addEventListener('click', () => setLightboxIndex(idx));
  });

  document.addEventListener('keydown', (e) => {
    if (!lightboxModal || !lightboxModal.classList.contains('open')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') setLightboxIndex(activeIndex - 1);
    if (e.key === 'ArrowRight') setLightboxIndex(activeIndex + 1);
  });
}

/* ==========================================================================
   PDP Variants, Stock Stepper & Add-to-Cart Validation
   ========================================================================== */
function initPDPVariantsAndCart() {
  const purchaseForm = document.getElementById('buybox-purchase-form');
  if (!purchaseForm) return;

  const variantsDataElem = document.getElementById('product-variants-json');
  let variants = [];
  if (variantsDataElem) {
    try {
      variants = JSON.parse(variantsDataElem.textContent);
    } catch(e) {}
  }

  const colorChips = document.querySelectorAll('.color-swatch-chip');
  const sizePills = document.querySelectorAll('.size-pill-btn');
  const selectedVariantIdInput = document.getElementById('selected-variant-id');
  const selectedSizeInput = document.getElementById('selected-size-input');
  const selectedColorInput = document.getElementById('selected-color-input');
  const selectedSizeLabel = document.getElementById('selected-size-label');
  const selectedColorLabel = document.getElementById('selected-color-label');
  const sizeErrorMsg = document.getElementById('size-error-msg');
  const colorErrorMsg = document.getElementById('color-error-msg');
  const displayedPrice = document.getElementById('displayed-price');
  const liveStockIndicator = document.getElementById('live-stock-indicator');
  const quantityInput = document.getElementById('pdp-quantity-input');
  const stepperMinus = document.getElementById('stepper-minus');
  const stepperPlus = document.getElementById('stepper-plus');
  const addToCartBtn = document.getElementById('pdp-add-to-cart-btn');
  const buyNowBtn = document.getElementById('pdp-buy-now-btn');

  let chosenSize = '';
  let chosenColor = '';

  function findMatchingVariant() {
    if (!variants || variants.length === 0) return null;
    return variants.find(v => {
      const matchSize = chosenSize ? v.size.toLowerCase() === chosenSize.toLowerCase() : true;
      const matchColor = chosenColor ? v.color_name.toLowerCase() === chosenColor.toLowerCase() : true;
      return matchSize && matchColor;
    });
  }

  function updateVariantUI() {
    const matched = findMatchingVariant();

    if (matched) {
      if (selectedVariantIdInput) selectedVariantIdInput.value = matched.id;
      if (matched.price && displayedPrice) displayedPrice.textContent = matched.price;

      // Update Stock Indicator
      if (liveStockIndicator) {
        if (matched.stock > 0) {
          if (matched.stock <= 5) {
            liveStockIndicator.innerHTML = `
              <span class="stock-badge low-stock">
                <span class="pulse-dot"></span> Only ${matched.stock} left in stock!
              </span>
            `;
          } else {
            liveStockIndicator.innerHTML = `
              <span class="stock-badge in-stock">
                <span class="check-dot">&#10003;</span> In Stock (${matched.stock} available)
              </span>
            `;
          }
          if (addToCartBtn) addToCartBtn.disabled = false;
          if (buyNowBtn) buyNowBtn.disabled = false;
        } else {
          liveStockIndicator.innerHTML = `
            <span class="stock-badge out-stock">&times; Out of stock for this selection</span>
          `;
          if (addToCartBtn) addToCartBtn.disabled = true;
          if (buyNowBtn) buyNowBtn.disabled = true;
        }
      }

      if (quantityInput) {
        quantityInput.max = matched.stock;
        if (parseInt(quantityInput.value, 10) > matched.stock) {
          quantityInput.value = Math.max(1, matched.stock);
        }
      }
    } else {
      if (selectedVariantIdInput) selectedVariantIdInput.value = '';
    }
  }

  // Color Swatch Selection
  colorChips.forEach(chip => {
    chip.addEventListener('click', () => {
      colorChips.forEach(c => c.classList.remove('selected'));
      chip.classList.add('selected');
      chosenColor = chip.dataset.color || '';
      if (selectedColorInput) selectedColorInput.value = chosenColor;
      if (selectedColorLabel) selectedColorLabel.textContent = chosenColor;
      if (colorErrorMsg) colorErrorMsg.textContent = '';
      updateVariantUI();
    });
  });

  // Size Pill Selection
  sizePills.forEach(pill => {
    pill.addEventListener('click', () => {
      sizePills.forEach(p => p.classList.remove('selected'));
      pill.classList.add('selected');
      chosenSize = pill.dataset.size || '';
      if (selectedSizeInput) selectedSizeInput.value = chosenSize;
      if (selectedSizeLabel) selectedSizeLabel.textContent = chosenSize;
      if (sizeErrorMsg) sizeErrorMsg.textContent = '';
      updateVariantUI();
    });
  });

  // Quantity Stepper
  function updateQuantity(delta) {
    if (!quantityInput) return;
    const current = parseInt(quantityInput.value || '1', 10);
    const min = parseInt(quantityInput.min || '1', 10);
    const max = parseInt(quantityInput.max || '999', 10);
    const nextVal = Math.min(max, Math.max(min, current + delta));
    quantityInput.value = nextVal;
  }

  if (stepperMinus) stepperMinus.addEventListener('click', () => updateQuantity(-1));
  if (stepperPlus) stepperPlus.addEventListener('click', () => updateQuantity(1));

  // Form Validation & Submission
  purchaseForm.addEventListener('submit', (e) => {
    let hasError = false;

    if (sizePills.length > 0 && !chosenSize) {
      hasError = true;
      if (sizeErrorMsg) sizeErrorMsg.textContent = 'Please select a size to continue.';
      const sizeSection = document.getElementById('size-selector-section');
      if (sizeSection) sizeSection.classList.add('error-shake');
    }

    if (colorChips.length > 0 && !chosenColor) {
      hasError = true;
      if (colorErrorMsg) colorErrorMsg.textContent = 'Please choose a color to continue.';
      const colorSection = document.getElementById('color-selector-section');
      if (colorSection) colorSection.classList.add('error-shake');
    }

    if (hasError) {
      e.preventDefault();
      showToast('Please select all required options (Size/Color) before adding to cart.', 'error');
      setTimeout(() => {
        document.querySelectorAll('.error-shake').forEach(el => el.classList.remove('error-shake'));
      }, 500);
      return;
    }
  });

  // Native Web Share API
  const shareBtn = document.getElementById('buybox-share-btn');
  if (shareBtn) {
    shareBtn.addEventListener('click', () => {
      if (navigator.share) {
        navigator.share({
          title: document.title,
          url: window.location.href,
        }).catch(() => {});
      } else {
        navigator.clipboard.writeText(window.location.href).then(() => {
          showToast('Product link copied to clipboard!', 'success');
        }).catch(() => {
          showToast('Share link copied: ' + window.location.href, 'info');
        });
      }
    });
  }

  // PDP Wishlist Toggle
  const pdpWishlistBtn = document.getElementById('pdp-wishlist-toggle-btn');
  if (pdpWishlistBtn) {
    pdpWishlistBtn.addEventListener('click', () => {
      const slug = pdpWishlistBtn.dataset.slug;
      const csrftoken = purchaseForm.querySelector('[name=csrfmiddlewaretoken]')?.value;

      fetch(`/wishlist/add/${slug}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json, text/html'
        }
      })
      .then(res => {
        if (res.ok) {
          const wasSaved = pdpWishlistBtn.classList.contains('saved');
          pdpWishlistBtn.classList.toggle('saved', !wasSaved);
          const txt = pdpWishlistBtn.querySelector('.wishlist-btn-text');
          if (txt) txt.textContent = wasSaved ? 'Add to Wishlist' : 'In Wishlist';
          const svgPath = pdpWishlistBtn.querySelector('svg');
          if (svgPath) svgPath.setAttribute('fill', wasSaved ? 'none' : 'currentColor');

          const badge = document.querySelector('.wishlist-count-badge');
          if (badge) {
            let current = parseInt(badge.textContent || '0', 10);
            current = wasSaved ? Math.max(0, current - 1) : current + 1;
            badge.textContent = current;
            badge.style.display = current > 0 ? 'inline-flex' : 'none';
          }

          showToast(wasSaved ? 'Product removed from wishlist.' : 'Saved to your wishlist!', 'success');
        } else {
          window.location.reload();
        }
      })
      .catch(() => window.location.reload());
    });
  }
}

/* ==========================================================================
   Size Chart Modal with CM / IN Toggle
   ========================================================================== */
function initSizeChartModal() {
  const openBtn = document.getElementById('open-size-chart-btn');
  const modal = document.getElementById('size-chart-modal');
  const closeBtn = document.getElementById('size-chart-close-btn');
  const backdrop = document.getElementById('size-chart-backdrop');
  if (!modal) return;

  function openModal() {
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  if (openBtn) openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);

  // Unit Toggle (CM vs IN)
  const unitBtns = modal.querySelectorAll('.unit-toggle-btn');
  const tableCm = document.getElementById('size-table-cm');
  const tableIn = document.getElementById('size-table-in');

  unitBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      unitBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const unit = btn.dataset.unit;
      if (unit === 'cm') {
        if (tableCm) tableCm.style.display = 'table';
        if (tableIn) tableIn.style.display = 'none';
      } else {
        if (tableCm) tableCm.style.display = 'none';
        if (tableIn) tableIn.style.display = 'table';
      }
    });
  });
}

/* ==========================================================================
   Sticky Mobile Add to Cart Bar
   ========================================================================== */
function initStickyMobileCart() {
  const stickyBar = document.getElementById('sticky-mobile-cart-bar');
  const mainCTA = document.getElementById('pdp-add-to-cart-btn');
  const stickyTrigger = document.getElementById('sticky-cart-trigger');

  if (!stickyBar || !mainCTA) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting && entry.boundingClientRect.top < 0) {
        stickyBar.classList.add('visible');
        stickyBar.setAttribute('aria-hidden', 'false');
      } else {
        stickyBar.classList.remove('visible');
        stickyBar.setAttribute('aria-hidden', 'true');
      }
    });
  }, { threshold: 0 });

  observer.observe(mainCTA);

  if (stickyTrigger) {
    stickyTrigger.addEventListener('click', () => {
      mainCTA.click();
    });
  }
}
