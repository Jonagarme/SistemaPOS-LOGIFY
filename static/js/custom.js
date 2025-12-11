// Sistema POS - Custom JavaScript

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Confirm delete actions
    $('.btn-delete').click(function(e) {
        if (!confirm('¿Está seguro que desea eliminar este registro?')) {
            e.preventDefault();
        }
    });
    
    // Format numbers as currency
    $('.currency').each(function() {
        var value = parseFloat($(this).text());
        if (!isNaN(value)) {
            $(this).text('L. ' + value.toFixed(2));
        }
    });
    
    // Search functionality
    $('.search-input').on('input', function() {
        var query = $(this).val();
        var target = $(this).data('target');
        
        if (query.length >= 2) {
            searchItems(query, target);
        } else {
            hideSearchResults();
        }
    });
    
    // Close search results when clicking outside
    $(document).click(function(e) {
        if (!$(e.target).closest('.search-container').length) {
            hideSearchResults();
        }
    });
});

// Search function
function searchItems(query, target) {
    $.ajax({
        url: '/buscar/',
        data: {
            'search': query,
            'target': target
        },
        success: function(data) {
            displaySearchResults(data);
        },
        error: function() {
            console.error('Error en la búsqueda');
        }
    });
}

// Display search results
function displaySearchResults(data) {
    var resultsContainer = $('.search-results');
    resultsContainer.empty();
    
    if (data.results && data.results.length > 0) {
        data.results.forEach(function(item) {
            var resultItem = $('<div class="search-result-item">')
                .text(item.name)
                .data('id', item.id)
                .click(function() {
                    selectSearchItem(item);
                });
            resultsContainer.append(resultItem);
        });
        resultsContainer.show();
    } else {
        resultsContainer.append('<div class="search-result-item">No se encontraron resultados</div>');
        resultsContainer.show();
    }
}

// Hide search results
function hideSearchResults() {
    $('.search-results').hide();
}

// Select search item
function selectSearchItem(item) {
    // Implementation depends on context
    hideSearchResults();
}

// Format currency input
function formatCurrency(input) {
    var value = input.value.replace(/[^\d.]/g, '');
    if (value) {
        input.value = parseFloat(value).toFixed(2);
    }
}

// Add to cart function (for POS)
function addToCart(productId, productName, price, stock) {
    var cartItems = $('#cart-items');
    var existingItem = cartItems.find('[data-product-id="' + productId + '"]');
    
    if (existingItem.length > 0) {
        // Increment quantity
        var qtyInput = existingItem.find('.quantity-input');
        var currentQty = parseInt(qtyInput.val());
        if (currentQty < stock) {
            qtyInput.val(currentQty + 1);
            updateCartItem(existingItem);
        } else {
            alert('Stock insuficiente');
        }
    } else {
        // Add new item
        var cartItem = $(`
            <div class="cart-item d-flex justify-content-between align-items-center mb-2" data-product-id="${productId}">
                <div class="flex-grow-1">
                    <div class="fw-bold">${productName}</div>
                    <small class="text-muted">L. ${price}</small>
                </div>
                <div class="d-flex align-items-center">
                    <input type="number" class="form-control form-control-sm quantity-input" 
                           value="1" min="1" max="${stock}" style="width: 60px;">
                    <button class="btn btn-sm btn-outline-danger ms-2 remove-item">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `);
        cartItems.append(cartItem);
    }
    
    updateCartTotal();
}

// Update cart item
function updateCartItem(item) {
    var quantity = parseInt(item.find('.quantity-input').val());
    var price = parseFloat(item.find('.text-muted').text().replace('L. ', ''));
    var total = quantity * price;
    
    // Update item display if needed
    updateCartTotal();
}

// Update cart total
function updateCartTotal() {
    var total = 0;
    $('#cart-items .cart-item').each(function() {
        var quantity = parseInt($(this).find('.quantity-input').val());
        var price = parseFloat($(this).find('.text-muted').text().replace('L. ', ''));
        total += quantity * price;
    });
    
    $('#cart-total').text('L. ' + total.toFixed(2));
}

// Remove item from cart
$(document).on('click', '.remove-item', function() {
    $(this).closest('.cart-item').remove();
    updateCartTotal();
});

// Update quantity
$(document).on('change', '.quantity-input', function() {
    updateCartItem($(this).closest('.cart-item'));
});

// Print function
function printContent(elementId) {
    var content = document.getElementById(elementId);
    var printWindow = window.open('', '', 'height=600,width=800');
    
    printWindow.document.write('<html><head><title>Imprimir</title>');
    printWindow.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">');
    printWindow.document.write('<style>body { font-size: 12px; } @media print { body { margin: 0; } }</style>');
    printWindow.document.write('</head><body>');
    printWindow.document.write(content.innerHTML);
    printWindow.document.write('</body></html>');
    
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
    printWindow.close();
}

// Validate form before submit
function validateForm(formId) {
    var form = document.getElementById(formId);
    var isValid = true;
    
    // Add custom validation logic here
    
    if (!isValid) {
        alert('Por favor, complete todos los campos requeridos');
        return false;
    }
    
    return true;
}

// Show loading spinner
function showLoading(element) {
    $(element).html('<span class="spinner-border spinner-border-sm" role="status"></span> Cargando...');
    $(element).prop('disabled', true);
}

// Hide loading spinner
function hideLoading(element, originalText) {
    $(element).html(originalText);
    $(element).prop('disabled', false);
}

// Format number with thousands separator
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Parse currency string to number
function parseCurrency(str) {
    return parseFloat(str.replace(/[^\d.-]/g, ''));
}