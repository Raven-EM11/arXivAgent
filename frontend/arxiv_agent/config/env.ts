export const ENV_CONFIG = {
  // development: {
    // API_BASE_URL: 'http://localhost:8000'
  // },
  //production: {
    API_BASE_URL: '/api'
  // },
} as const;

export const getApiBaseUrl = () => {
  // const env = process.env.NODE_ENV || 'development';
  // return ENV_CONFIG[env as keyof typeof ENV_CONFIG].API_BASE_URL;
  return ENV_CONFIG.API_BASE_URL;
}; 