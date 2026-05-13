/**
 * HTTP请求工具 - 使用相对路径，依赖代理转发到后端
 * 
 * 401 拦截：当认证令牌无效或过期时，自动清理本地存储并跳转到登录页。
 * 这解决了 JWT 迁移后浏览器 localStorage 中残留旧 base64 token 的问题。
 */

const API_PREFIX = '/api/v1';

/** 清理认证状态并跳转登录，避免无限循环 */
function clearAuthAndRedirect() {
  if (typeof window === 'undefined') return;
  // 防止在登录页重复清理导致循环
  if (window.location.pathname === '/login') return;
  
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  localStorage.removeItem('class');
  // 用 replace 避免回退到需要认证的页面
  window.location.replace('/login');
}

class HttpClient {
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    
    return headers;
  }

  private getUrl(path: string): string {
    if (path.startsWith('/api/v1')) {
      return path;
    }
    if (path.startsWith('/')) {
      return `${API_PREFIX}${path}`;
    }
    return `${API_PREFIX}/${path}`;
  }

  private async handleError(response: Response): Promise<never> {
    let errorMsg = `HTTP error! status: ${response.status}`;
    
    // 401 拦截：令牌无效或过期 → 清理状态，跳转登录
    if (response.status === 401) {
      clearAuthAndRedirect();
    }

    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const error = await response.json();
        if (error.detail) {
          if (Array.isArray(error.detail)) {
            errorMsg = error.detail.map((e: Record<string, unknown>) => e.msg).join('; ');
          } else if (typeof error.detail === 'string') {
            errorMsg = error.detail;
          }
        } else if (error.message) {
          errorMsg = error.message;
        }
      } else {
        const text = await response.text();
        if (text) {
          if (text.includes('<html')) {
            errorMsg = `Server returned HTML page (status ${response.status})`;
          } else {
            errorMsg = text.substring(0, 200);
          }
        }
      }
    } catch (parseError) {
      errorMsg = `HTTP error! status: ${response.status}, unable to parse error response`;
    }
    
    throw new Error(errorMsg);
  }

  async get<T = unknown>(path: string): Promise<T> {
    const response = await fetch(this.getUrl(path), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    if (response.status === 204) {
      return null as T;
    }

    try {
      return await response.json();
    } catch (e) {
      throw new Error('Failed to parse JSON response from GET ' + path);
    }
  }

  async post<T = unknown>(path: string, data?: Record<string, unknown>): Promise<T> {
    const response = await fetch(this.getUrl(path), {
      method: 'POST',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    if (response.status === 204) {
      return null as T;
    }

    try {
      return await response.json();
    } catch (e) {
      throw new Error('Failed to parse JSON response from POST ' + path);
    }
  }

  async put<T = unknown>(path: string, data?: Record<string, unknown>): Promise<T> {
    const response = await fetch(this.getUrl(path), {
      method: 'PUT',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    if (response.status === 204) {
      return null as T;
    }

    try {
      return await response.json();
    } catch (e) {
      throw new Error('Failed to parse JSON response from PUT ' + path);
    }
  }

  async delete<T = unknown>(path: string): Promise<T> {
    const response = await fetch(this.getUrl(path), {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    if (response.status === 204) {
      return null as T;
    }

    try {
      return await response.json();
    } catch (e) {
      throw new Error('Failed to parse JSON response from DELETE ' + path);
    }
  }
}

const http = new HttpClient();
export { http, HttpClient };
