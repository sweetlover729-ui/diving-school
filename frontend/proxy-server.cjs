/**
 * API 代理服务器 - 独立于 Next.js standalone
 * 将 /api/ 和 /static/ 请求代理到后端，其余请求转发给 Next.js standalone
 */
const http = require('http');
const { spawn } = require('child_process');

const PORT = parseInt(process.env.PORT || '3099', 10);
const BACKEND = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const NEXT_PORT = PORT + 1; // standalone 监听在内网端口

// 启动 Next.js standalone server
const nextServer = spawn('node', ['.next/standalone/server.js'], {
  env: { ...process.env, PORT: String(NEXT_PORT) },
  stdio: ['ignore', 'pipe', 'pipe'],
});
nextServer.stdout.on('data', d => process.stdout.write(d));
nextServer.stderr.on('data', d => process.stderr.write(d));

const backendUrl = new URL(BACKEND);

const server = http.createServer((clientReq, clientRes) => {
  const { method, url, headers } = clientReq;

  // 代理 /api/ 和 /static/ 到后端
  if (url.startsWith('/api/') || url.startsWith('/static/')) {
    const proxyReq = http.request({
      hostname: backendUrl.hostname,
      port: backendUrl.port,
      path: url,
      method,
      headers: { ...headers, host: `${backendUrl.hostname}:${backendUrl.port}` },
    }, (proxyRes) => {
      clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(clientRes);
    });
    proxyReq.on('error', (err) => {
      console.error('[proxy] backend error:', err.message);
      clientRes.writeHead(502);
      clientRes.end('Bad Gateway');
    });
    clientReq.pipe(proxyReq);
    return;
  }

  // 其他请求转发给 Next.js standalone
  const nextReq = http.request({
    hostname: '127.0.0.1',
    port: NEXT_PORT,
    path: url,
    method,
    headers,
  }, (nextRes) => {
    clientRes.writeHead(nextRes.statusCode, nextRes.headers);
    nextRes.pipe(clientRes);
  });
  nextReq.on('error', (err) => {
    console.error('[proxy] next error:', err.message);
    clientRes.writeHead(502);
    clientRes.end('Bad Gateway');
  });
  clientReq.pipe(nextReq);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[proxy] listening on http://0.0.0.0:${PORT}`);
  console.log(`[proxy] backend -> ${BACKEND}`);
  console.log(`[proxy] next.js  -> http://127.0.0.1:${NEXT_PORT}`);
});

// 优雅退出
process.on('SIGTERM', () => {
  nextServer.kill('SIGTERM');
  server.close();
});
process.on('SIGINT', () => {
  nextServer.kill('SIGTERM');
  server.close();
});
