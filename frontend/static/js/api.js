// Smart Wardrobe - API Client
// Centralized API communication with configurable base URL

const API_CONFIG = {
    // Base URL will be set dynamically from environment or detected
    baseUrl: window.SMART_WARDROBE_API_URL || '',
    
    // Timeout for requests (ms)
    timeout: 30000,
    
    // Retry configuration
    retryAttempts: 3,
    retryDelay: 1000
};

/**
 * API Client for Smart Wardrobe
 * Provides unified interface for all backend endpoints
 */
class ApiClient {
    constructor(config = {}) {
        this.config = { ...API_CONFIG, ...config };
        this.baseUrl = this.config.baseUrl;
    }
    
    /**
     * Set the base URL for API requests
     * @param {string} url - Base URL (e.g., 'http://192.168.1.100:8080/api/v1')
     */
    setBaseUrl(url) {
        this.baseUrl = url.replace(/\/$/, '');
    }
    
    /**
     * Make HTTP request with error handling and retry logic
     * @param {string} path - API endpoint path
     * @param {Object} options - Fetch options
     * @returns {Promise<any>} Response data
     */
    async request(path, options = {}) {
        const url = `${this.baseUrl}${path}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        let lastError;
        for (let attempt = 0; attempt <= this.config.retryAttempts; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);
                
                const response = await fetch(url, {
                    ...mergedOptions,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
                    throw new ApiError(response.status, errorData.detail || 'Error desconocido');
                }
                
                // Handle 204 No Content
                if (response.status === 204) {
                    return null;
                }
                
                return await response.json();
                
            } catch (error) {
                lastError = error;
                
                // Don't retry on client errors (4xx)
                if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
                    throw error;
                }
                
                // Don't retry on abort
                if (error.name === 'AbortError') {
                    throw new ApiError(0, 'Tiempo de espera agotado');
                }
                
                // Wait before retry
                if (attempt < this.config.retryAttempts) {
                    await this.sleep(this.config.retryDelay * (attempt + 1));
                }
            }
        }
        
        throw lastError;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // ========== GARMENTS ==========
    
    async getGarments(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/garments${query ? `?${query}` : ''}`);
    }
    
    async getGarment(id) {
        return this.request(`/garments/${id}`);
    }
    
    async createGarment(formData) {
        return this.request('/garments', {
            method: 'POST',
            body: formData,
            headers: {} // Let browser set Content-Type for FormData
        });
    }
    
    async updateGarment(id, data) {
        return this.request(`/garments/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }
    
    async deleteGarment(id) {
        return this.request(`/garments/${id}`, { method: 'DELETE' });
    }
    
    async bulkDeleteGarments(ids) {
        return this.request('/garments/bulk-delete', {
            method: 'DELETE',
            body: JSON.stringify({ ids })
        });
    }
    
    // ========== OUTFITS ==========
    
    async getOutfits(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/outfits${query ? `?${query}` : ''}`);
    }
    
    async getOutfit(id) {
        return this.request(`/outfits/${id}`);
    }
    
    async createOutfit(data) {
        return this.request('/outfits', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async updateOutfit(id, data) {
        return this.request(`/outfits/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }
    
    async deleteOutfit(id) {
        return this.request(`/outfits/${id}`, { method: 'DELETE' });
    }
    
    // ========== RECOMMENDATIONS ==========
    
    async recommendOutfits(request) {
        return this.request('/recommend/outfits', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    }
    
    async enhanceRecommendation(request) {
        return this.request('/enhance', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    }
    
    // ========== FEEDBACK ==========
    
    async rateOutfit(data) {
        return this.request('/feedback/outfit', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async rateGarment(data) {
        return this.request('/feedback/garment', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    // Backend only exposes POST feedback endpoints; these GETs don't exist.
    // async getOutfitFeedback(outfitId) {
    //     return this.request(`/feedback/outfit/${outfitId}`);
    // }
    //
    // async getGarmentFeedback(garmentId) {
    //     return this.request(`/feedback/garment/${garmentId}`);
    // }
    
    // ========== PACKING ==========
    
    async createPackingPlan(request) {
        return this.request('/recommend/packing', {
            method: 'POST',
            body: JSON.stringify(request)
        });
    }
    
    // ========== STYLE RULES ==========
    
    async getRules(activeOnly = true) {
        return this.request(`/rules?active_only=${activeOnly}`);
    }
    
    async getRule(id) {
        return this.request(`/rules/${id}`);
    }
    
    async createRule(data) {
        return this.request('/rules', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async updateRule(id, data) {
        return this.request(`/rules/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }
    
    async deleteRule(id) {
        return this.request(`/rules/${id}`, { method: 'DELETE' });
    }
    
    // ========== HEALTH ==========
    
    async healthCheck() {
        return this.request('/health');
    }
}

/**
 * API Error class for structured error handling
 */
class ApiError extends Error {
    constructor(status, message, data = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
    
    get isNetworkError() {
        return this.status === 0;
    }
    
    get isTimeout() {
        return this.message.includes('Tiempo de espera');
    }
    
    get isClientError() {
        return this.status >= 400 && this.status < 500;
    }
    
    get isServerError() {
        return this.status >= 500;
    }
}

// Export singleton instance
const api = new ApiClient();

// Export for ES modules
export { ApiClient, ApiError, api };

// Also export for global/window
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ApiClient, ApiError, api };
} else {
    window.ApiClient = ApiClient;
    window.ApiError = ApiError;
    window.api = api;
}