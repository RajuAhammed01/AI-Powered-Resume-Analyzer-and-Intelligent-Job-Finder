/**
 * JobSnap Enterprise REST API Client & Frontend Interaction Controller
 */
(function() {
    'use strict';

    // Helper to retrieve CSRF token from meta tag
    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Toast notification UI
    var JobSnapToast = {
        container: null,
        init: function() {
            if (!this.container) {
                var el = document.createElement('div');
                el.id = 'jobsnap-toast-container';
                el.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;pointer-events:none;';
                document.body.appendChild(el);
                this.container = el;
            }
        },
        show: function(message, type) {
            this.init();
            type = type || 'info';
            var toast = document.createElement('div');
            toast.style.cssText = 'pointer-events:auto;min-width:260px;max-width:380px;padding:12px 18px;border-radius:10px;' +
                'box-shadow:0 10px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1);' +
                'display:flex;align-items:center;gap:12px;font-family:Inter,sans-serif;font-size:0.875rem;' +
                'opacity:0;transform:translateY(12px);transition:all 0.25s cubic-bezier(0.16,1,0.3,1);color:#ffffff;';

            if (type === 'success') {
                toast.style.backgroundColor = '#16866A'; // Success Teal
                toast.innerHTML = '<i class="fa-solid fa-circle-check"></i> <span>' + message + '</span>';
            } else if (type === 'error') {
                toast.style.backgroundColor = '#D9535D'; // Error Red
                toast.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> <span>' + message + '</span>';
            } else {
                toast.style.backgroundColor = '#14243B'; // Navy Blue
                toast.innerHTML = '<i class="fa-solid fa-circle-info"></i> <span>' + message + '</span>';
            }

            this.container.appendChild(toast);

            // Animate entrance
            requestAnimationFrame(function() {
                toast.style.opacity = '1';
                toast.style.transform = 'translateY(0)';
            });

            // Auto dismiss after 3.5s
            setTimeout(function() {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(12px)';
                setTimeout(function() {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, 3500);
        }
    };

    // REST API communication abstraction
    var JobSnapAPI = {
        baseUrl: '/api/v1',

        request: function(endpoint, options) {
            options = options || {};
            var url = this.baseUrl + endpoint;
            var headers = {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };

            var csrf = getCsrfToken();
            if (csrf) {
                headers['X-CSRFToken'] = csrf;
            }

            if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(options.body);
            }

            options.headers = Object.assign(headers, options.headers || {});

            return fetch(url, options).then(function(response) {
                return response.json().then(function(data) {
                    if (!response.ok) {
                        var err = new Error(data && data.error && data.error.message ? data.error.message : 'API request failed');
                        err.status = response.status;
                        err.data = data;
                        throw err;
                    }
                    return data;
                });
            });
        },

        // Search jobs asynchronously
        searchJobs: function(params) {
            var qs = new URLSearchParams(params || {}).toString();
            return this.request('/jobs/search' + (qs ? '?' + qs : ''), { method: 'GET' });
        },

        // Retrieve single job details
        getJob: function(jobId) {
            return this.request('/jobs/' + encodeURIComponent(jobId), { method: 'GET' });
        },

        // Save a job asynchronously
        saveJob: function(jobId, jobData) {
            var payload = Object.assign({ job_id: jobId }, jobData || {});
            return this.request('/jobs/save', {
                method: 'POST',
                body: payload
            });
        },

        // Remove a saved job
        unsaveJob: function(jobId) {
            return this.request('/jobs/save/' + encodeURIComponent(jobId), {
                method: 'DELETE'
            });
        },

        // Record apply intent
        trackApplyIntent: function(jobId, jobData) {
            var payload = Object.assign({ job_id: jobId }, jobData || {});
            return this.request('/jobs/apply-intent', {
                method: 'POST',
                body: payload
            });
        },

        // System health check
        checkHealth: function() {
            return this.request('/health', { method: 'GET' });
        }
    };

    // Bind AJAX interactions across pages
    document.addEventListener('DOMContentLoaded', function() {
        // Intercept async bookmarking buttons
        document.querySelectorAll('.js-save-job-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                var jobId = btn.getAttribute('data-job-id');
                if (!jobId) return;

                var isSaved = btn.getAttribute('data-is-saved') === 'true';
                var icon = btn.querySelector('i');

                if (isSaved) {
                    JobSnapAPI.unsaveJob(jobId).then(function() {
                        btn.setAttribute('data-is-saved', 'false');
                        if (icon) {
                            icon.className = 'fa-regular fa-bookmark';
                        }
                        btn.classList.remove('active');
                        JobSnapToast.show('Job removed from your saved list.', 'info');
                    }).catch(function(err) {
                        JobSnapToast.show(err.message || 'Could not update bookmark.', 'error');
                    });
                } else {
                    JobSnapAPI.saveJob(jobId, {
                        job_title: btn.getAttribute('data-job-title') || '',
                        company: btn.getAttribute('data-job-company') || '',
                        location: btn.getAttribute('data-job-location') || '',
                        job_apply_link: btn.getAttribute('data-job-url') || ''
                    }).then(function() {
                        btn.setAttribute('data-is-saved', 'true');
                        if (icon) {
                            icon.className = 'fa-solid fa-bookmark';
                        }
                        btn.classList.add('active');
                        JobSnapToast.show('Job bookmarked to Saved Jobs!', 'success');
                    }).catch(function(err) {
                        JobSnapToast.show(err.message || 'Could not save job.', 'error');
                    });
                }
            });
        });
    });

    // Expose on global window object
    window.JobSnapAPI = JobSnapAPI;
    window.JobSnapToast = JobSnapToast;
})();

