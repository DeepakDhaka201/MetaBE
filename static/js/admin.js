// MetaX Admin Panel JavaScript

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

    // Confirm dialogs for dangerous actions
    $('.btn-danger, .btn-outline-danger').click(function(e) {
        if ($(this).data('confirm')) {
            if (!confirm($(this).data('confirm'))) {
                e.preventDefault();
                return false;
            }
        }
    });

    // Loading states for buttons
    $('.btn-loading').click(function() {
        var btn = $(this);
        var originalText = btn.html();
        btn.html('<span class="loading-spinner"></span> Loading...');
        btn.prop('disabled', true);
        
        // Re-enable after 3 seconds (fallback)
        setTimeout(function() {
            btn.html(originalText);
            btn.prop('disabled', false);
        }, 3000);
    });

    // Search functionality
    $('#searchInput').on('keyup', function() {
        var value = $(this).val().toLowerCase();
        $('#dataTable tbody tr').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
    });

    // Auto-refresh functionality
    if ($('[data-auto-refresh]').length > 0) {
        var refreshInterval = $('[data-auto-refresh]').data('auto-refresh') * 1000;
        setInterval(function() {
            location.reload();
        }, refreshInterval);
    }
});

// Utility Functions
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 6
    }).format(amount);
}

function formatNumber(number) {
    return new Intl.NumberFormat('en-US').format(number);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// AJAX Helper Functions
function makeAjaxRequest(url, method = 'GET', data = null, successCallback = null, errorCallback = null) {
    $.ajax({
        url: url,
        method: method,
        data: data,
        dataType: 'json',
        success: function(response) {
            if (successCallback) {
                successCallback(response);
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX Error:', error);
            if (errorCallback) {
                errorCallback(xhr, status, error);
            } else {
                showAlert('An error occurred. Please try again.', 'danger');
            }
        }
    });
}

function showAlert(message, type = 'info') {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts
    $('.alert').remove();
    
    // Add new alert at the top of the container
    $('.container-fluid').prepend(alertHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
}

// Chart Helper Functions
function createLineChart(canvasId, labels, datasets, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(0,0,0,0.1)'
                }
            },
            x: {
                grid: {
                    color: 'rgba(0,0,0,0.1)'
                }
            }
        },
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false,
            }
        }
    };

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: { ...defaultOptions, ...options }
    });
}

function createDoughnutChart(canvasId, labels, data, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
            }
        }
    };

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#007bff',
                    '#28a745',
                    '#ffc107',
                    '#dc3545',
                    '#17a2b8',
                    '#6c757d'
                ],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: { ...defaultOptions, ...options }
    });
}

// Form Validation
function validateForm(formId) {
    var form = document.getElementById(formId);
    var isValid = true;
    
    // Remove existing error messages
    $('.invalid-feedback').remove();
    $('.is-invalid').removeClass('is-invalid');
    
    // Check required fields
    $(form).find('[required]').each(function() {
        if (!$(this).val().trim()) {
            $(this).addClass('is-invalid');
            $(this).after('<div class="invalid-feedback">This field is required.</div>');
            isValid = false;
        }
    });
    
    // Check email fields
    $(form).find('input[type="email"]').each(function() {
        var email = $(this).val().trim();
        if (email && !isValidEmail(email)) {
            $(this).addClass('is-invalid');
            $(this).after('<div class="invalid-feedback">Please enter a valid email address.</div>');
            isValid = false;
        }
    });
    
    return isValid;
}

function isValidEmail(email) {
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Data Table Enhancement
function enhanceDataTable(tableId) {
    var table = $('#' + tableId);
    
    // Add sorting functionality
    table.find('th[data-sort]').click(function() {
        var column = $(this).data('sort');
        var order = $(this).hasClass('sort-asc') ? 'desc' : 'asc';
        
        // Remove existing sort classes
        table.find('th').removeClass('sort-asc sort-desc');
        
        // Add new sort class
        $(this).addClass('sort-' + order);
        
        // Sort table rows
        sortTable(tableId, column, order);
    });
}

function sortTable(tableId, column, order) {
    var table = $('#' + tableId);
    var rows = table.find('tbody tr').get();
    
    rows.sort(function(a, b) {
        var aVal = $(a).find('td').eq(column).text().trim();
        var bVal = $(b).find('td').eq(column).text().trim();
        
        // Try to parse as numbers
        var aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
        var bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return order === 'asc' ? aNum - bNum : bNum - aNum;
        } else {
            return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
    });
    
    $.each(rows, function(index, row) {
        table.find('tbody').append(row);
    });
}
