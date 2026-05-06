import axios from 'axios';

// 创建一个专门的 axios 实例
const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api', // 你的 Flask 后端地址
  timeout: 5000
});

// 🚀 请求拦截器：发请求前会自动执行这里
api.interceptors.request.use(
  config => {
    // 从浏览器的本地存储中拿出我们的“金钥匙”
    const token = localStorage.getItem('access_token');
    
    // 如果有钥匙，就把它按规范塞进请求头里 (和 Postman 里的 Bearer Token 一模一样)
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 🛡️ 响应拦截器：处理服务器返回的结果 (比如发现 Token 过期了)
api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    if (error.response && error.response.status === 401) {
      // 如果后端返回 401，说明没登录或者 Token 过期了
      console.error("认证失败，请重新登录");
      // 这里未来可以加上自动跳回登录页面的逻辑
      // localStorage.removeItem('access_token');
      // window.location.href = '/login'; 
    }
    return Promise.reject(error);
  }
);

export default api;
// ... 上面的拦截器代码 ...

// 注册 API
export const registerUser = (userData) => {
  return api.post('/register', userData);
};

// 登录 API
export const loginUser = (credentials) => {
  return api.post('/login', credentials);
};

// 获取受保护的后台数据 (测试用)
export const getAdminDashboard = () => {
  return api.get('/admin/dashboard');
};