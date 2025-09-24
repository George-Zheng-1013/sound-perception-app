const { app, BrowserWindow, dialog, session } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const fs = require('fs')
const url = require('url')
const isDev = process.env.NODE_ENV === 'development'
const os = require('os')

let mainWindow = null
let pythonProcess = null
let localServer = null

// MIME 类型映射
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject'
}

function startLocalServer() {
  return new Promise((resolve, reject) => {
    const port = 8080
    const distPath = path.join(__dirname, '../dist')
    
    console.log('=== Starting Local Server ===')
    console.log('Port:', port)
    console.log('Dist path:', distPath)
    console.log('Dist exists:', fs.existsSync(distPath))
    
    // 检查 dist 目录内容
    if (fs.existsSync(distPath)) {
      const files = fs.readdirSync(distPath)
      console.log('Dist contents:', files)
      
      // 检查 index.html 是否存在
      const indexPath = path.join(distPath, 'index.html')
      console.log('index.html exists:', fs.existsSync(indexPath))
    }
    
    localServer = http.createServer((req, res) => {
      let pathname = url.parse(req.url).pathname
      console.log('Request:', pathname)
      
      if (pathname === '/') {
        pathname = '/index.html'
      }
      
      const filePath = path.join(distPath, pathname)
      console.log('Serving:', filePath)
      
      // 检查文件是否存在
      fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
          console.error('File not found:', filePath)
          res.writeHead(404, { 'Content-Type': 'text/plain' })
          res.end('Not Found')
          return
        }
        
        // 读取文件
        fs.readFile(filePath, (err, data) => {
          if (err) {
            console.error('Error reading file:', err)
            res.writeHead(500, { 'Content-Type': 'text/plain' })
            res.end('Internal Server Error')
            return
          }
          
          const ext = path.extname(filePath).toLowerCase()
          const mimeType = mimeTypes[ext] || 'application/octet-stream'
          
          res.writeHead(200, { 
            'Content-Type': mimeType,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          })
          res.end(data)
        })
      })
    })
    
    localServer.listen(port, '127.0.0.1', (err) => {
      if (err) {
        console.error('Server listen error:', err)
        reject(err)
      } else {
        console.log(`✓ Local server running on http://127.0.0.1:${port}`)
        resolve(`http://127.0.0.1:${port}`)
      }
    })
    
    localServer.on('error', (err) => {
      console.error('Server error:', err)
      reject(err)
    })
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    icon: path.join(__dirname, '../public/favicon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
      allowRunningInsecureContent: true,
      experimentalFeatures: true
    },
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5175')
    mainWindow.webContents.openDevTools()
  } else {
    // 生产环境：确保先启动服务器
    console.log('Production mode: starting local server...')
    
    startLocalServer()
      .then((serverUrl) => {
        console.log('✓ Local server started successfully:', serverUrl)
        console.log('Loading from local server...')
        
        // 等待一下再加载，确保服务器完全启动
        setTimeout(() => {
          mainWindow.loadURL(serverUrl)
          mainWindow.webContents.openDevTools() // 临时调试用
        }, 500)
      })
      .catch((err) => {
        console.error('✗ Failed to start local server:', err)
        
        // 如果服务器启动失败，尝试不同的方法
        console.log('Trying alternative approach...')
        
        // 方法1：尝试不同端口
        startLocalServerWithPort(8081)
          .then((serverUrl) => {
            console.log('✓ Alternative server started:', serverUrl)
            mainWindow.loadURL(serverUrl)
          })
          .catch(() => {
            // 方法2：最后回退方案
            console.log('All server attempts failed, using file protocol with workaround...')
            loadFileWithWorkaround()
          })
      })
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  // 添加更详细的错误处理
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error('页面加载失败:', errorDescription, validatedURL)
    console.error('Error code:', errorCode)
  })

  mainWindow.webContents.on('dom-ready', () => {
    console.log('DOM ready')
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    // 关闭本地服务器
    if (localServer) {
      localServer.close()
      localServer = null
    }
  })
}

// 尝试不同端口的服务器
function startLocalServerWithPort(port) {
  return new Promise((resolve, reject) => {
    const distPath = path.join(__dirname, '../dist')
    
    console.log(`Trying to start server on port ${port}`)
    
    const server = http.createServer((req, res) => {
      let pathname = url.parse(req.url).pathname
      
      if (pathname === '/') {
        pathname = '/index.html'
      }
      
      const filePath = path.join(distPath, pathname)
      console.log('Serving file:', filePath)
      
      fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
          console.error('File not found:', filePath)
          res.writeHead(404, { 'Content-Type': 'text/plain' })
          res.end('Not Found')
          return
        }
        
        fs.readFile(filePath, (err, data) => {
          if (err) {
            console.error('Error reading file:', err)
            res.writeHead(500, { 'Content-Type': 'text/plain' })
            res.end('Internal Server Error')
            return
          }
          
          const ext = path.extname(filePath).toLowerCase()
          const mimeType = mimeTypes[ext] || 'application/octet-stream'
          
          res.writeHead(200, { 
            'Content-Type': mimeType,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          })
          res.end(data)
        })
      })
    })
    
    server.listen(port, '127.0.0.1', (err) => {
      if (err) {
        reject(err)
      } else {
        localServer = server
        resolve(`http://127.0.0.1:${port}`)
      }
    })
    
    server.on('error', (err) => {
      reject(err)
    })
  })
}

// 最后的回退方案
function loadFileWithWorkaround() {
  console.log('Using file protocol workaround...')
  
  // 创建临时的 HTML 内容，内联所有资源
  const distPath = path.join(__dirname, '../dist')
  const indexPath = path.join(distPath, 'index.html')
  
  fs.readFile(indexPath, 'utf8', (err, htmlContent) => {
    if (err) {
      console.error('Cannot read index.html:', err)
      return
    }
    
    // 尝试内联资源或使用 data URLs
    // 这是一个复杂的方案，先试试简单的加载
    mainWindow.loadFile(indexPath)
  })
}

function validatePaths() {
  const electronDir = __dirname  // .../Sound-perception-system-front-end/electron
  
  // 修正路径计算
  let pclaeDir
  
  if (isDev) {
    // 开发环境：从 electron 目录向上两级到项目根目录
    pclaeDir = path.join(__dirname, '..', '..', 'PCLAE-CTPN')
  } else {
    // 生产环境：从 exe 文件位置计算
    // 当前 __dirname 是在 resources/app.asar/electron
    // 需要找到实际的项目根目录
    
    // 方法1：从 process.cwd() 计算（exe 运行目录）
    const exeDir = process.cwd()  // dist-electron/win-unpacked
    const distElectronDir = path.dirname(exeDir)  // dist-electron
    const frontendDir = path.dirname(distElectronDir)  // Sound-perception-system-front-end
    const projectRoot = path.dirname(frontendDir)  // sound-perception-app
    pclaeDir = path.join(projectRoot, 'PCLAE-CTPN')
    
    // 如果方法1失败，尝试方法2
    if (!fs.existsSync(pclaeDir)) {
      // 方法2：从 process.execPath 计算
      const execPath = process.execPath  // .../win-unpacked/声音感知识别系统.exe
      const winUnpackedDir = path.dirname(execPath)  // win-unpacked
      const distElectronDir2 = path.dirname(winUnpackedDir)  // dist-electron
      const frontendDir2 = path.dirname(distElectronDir2)  // Sound-perception-system-front-end
      const projectRoot2 = path.dirname(frontendDir2)  // sound-perception-app
      pclaeDir = path.join(projectRoot2, 'PCLAE-CTPN')
    }
  }
  
  console.log('=== 路径验证 ===')
  console.log('isDev:', isDev)
  console.log('__dirname:', __dirname)
  console.log('process.cwd():', process.cwd())
  console.log('process.execPath:', process.execPath)
  console.log('计算出的 PCLAE-CTPN dir:', pclaeDir)
  console.log('PCLAE-CTPN exists:', fs.existsSync(pclaeDir))
  
  // 如果还是找不到，尝试更多可能的路径
  if (!fs.existsSync(pclaeDir)) {
    const possiblePaths = [
      path.join(__dirname, '..', '..', 'PCLAE-CTPN'),
      path.join(__dirname, '..', '..', '..', 'PCLAE-CTPN'),
      path.join(__dirname, '..', '..', '..', '..', 'PCLAE-CTPN'),
      path.join(process.cwd(), '..', '..', 'PCLAE-CTPN'),
      path.join(path.dirname(process.execPath), '..', '..', '..', 'PCLAE-CTPN')
    ]
    
    console.log('=== 尝试其他可能的路径 ===')
    for (const testPath of possiblePaths) {
      const normalized = path.normalize(testPath)
      const exists = fs.existsSync(normalized)
      console.log(`${normalized}: ${exists ? '✓' : '✗'}`)
      
      if (exists) {
        pclaeDir = normalized
        break
      }
    }
  }
  
  return pclaeDir
}

function startPythonBackend() {
  console.log('=== startPythonBackend 函数被调用 ===')
  
  try {
    console.log('=== Starting Python Backend via start.bat ===')
    
    const pclaeDir = validatePaths()
    console.log('validatePaths 返回:', pclaeDir)
    
    if (!pclaeDir) {
      console.error('validatePaths 返回了空值')
      dialog.showErrorBox('路径错误', 'validatePaths 返回了空值')
      return
    }
    
    if (!fs.existsSync(pclaeDir)) {
      const errorMsg = `找不到 PCLAE-CTPN 目录: ${pclaeDir}`
      console.error(errorMsg)
      dialog.showErrorBox('路径错误', errorMsg)
      return
    }
    
    const startBatPath = path.join(pclaeDir, 'start.bat')

    console.log('=== 最终路径信息 ===')
    console.log('PCLAE-CTPN directory:', pclaeDir)
    console.log('Batch script path:', startBatPath)
    console.log('Directory exists:', fs.existsSync(pclaeDir))
    console.log('Batch script exists:', fs.existsSync(startBatPath))

    // 如果 start.bat 不存在，直接返回
    if (!fs.existsSync(startBatPath)) {
      const errorMsg = `start.bat 文件不存在: ${startBatPath}`
      console.error(errorMsg)
      dialog.showErrorBox('文件错误', errorMsg)
      return
    }

    // 检查重要文件是否存在
    const importantFiles = [
      'start.bat',
      'testaudio.py', 
      'setup.py',
      'CLAP_weights_2023.pth',
      'category_mapping.csv'
    ]
    
    console.log('=== 检查重要文件 ===')
    let missingCriticalFiles = []
    
    for (const file of importantFiles) {
      const filePath = path.join(pclaeDir, file)
      const exists = fs.existsSync(filePath)
      console.log(`${file}: ${exists ? '✓' : '✗'} (${filePath})`)
      
      if (!exists && ['start.bat', 'testaudio.py'].includes(file)) {
        missingCriticalFiles.push(file)
      }
    }
    
    if (missingCriticalFiles.length > 0) {
      const errorMsg = `关键文件缺失: ${missingCriticalFiles.join(', ')}\n路径: ${pclaeDir}`
      console.error(errorMsg)
      dialog.showErrorBox('文件错误', errorMsg)
      return
    }

    // 使用 cmd 执行 batch 脚本
    console.log('=== 准备启动后端进程 ===')
    console.log('执行命令:', `cmd /c "${startBatPath}"`)
    console.log('工作目录:', pclaeDir)
    
    pythonProcess = spawn('cmd', ['/c', `"${startBatPath}"`], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: pclaeDir,  // 工作目录设为 PCLAE-CTPN
      shell: true,
      windowsHide: false  // 显示命令行窗口，方便调试
    })

    console.log('=== spawn 命令已执行 ===')
    console.log('进程 PID:', pythonProcess.pid)

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString()
      console.log(`后端输出: ${output}`)
      
      // 检测服务器启动成功的标志
      if (output.includes('Running on') || output.includes('* Serving Flask app') || output.includes('启动音频分析服务器')) {
        console.log('✓ Python后端服务器启动成功')
      }
    })

    pythonProcess.stderr.on('data', (data) => {
      console.error(`后端错误: ${data.toString()}`)
    })

    pythonProcess.on('close', (code) => {
      console.log(`后端进程退出，代码: ${code}`)
      if (code !== 0) {
        console.error('后端进程异常退出')
      }
    })

    pythonProcess.on('error', (err) => {
      console.error('无法启动后端进程:', err)
      dialog.showErrorBox('启动错误', `无法启动Python后端服务: ${err.message}`)
    })

    pythonProcess.on('spawn', () => {
      console.log('✓ 后端进程启动成功')
    })
    
  } catch (error) {
    console.error('startPythonBackend 函数执行时发生异常:', error)
    dialog.showErrorBox('异常错误', `后端启动异常: ${error.message}`)
  }
}

app.whenReady().then(() => {
  console.log('=== App Ready ===')
  
  // 设置 Content Security Policy
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': ['default-src \'self\' \'unsafe-inline\' \'unsafe-eval\' data: blob: file: http: https:']
      }
    })
  })

  createWindow()
  
  // 验证路径并启动后端
  console.log('=== 准备启动后端 ===')
  setTimeout(() => {
    console.log('=== 1秒延迟后，开始启动后端 ===')
    try {
      startPythonBackend()
    } catch (err) {
      console.error('启动后端时发生错误:', err)
      dialog.showErrorBox('启动错误', `启动后端时发生错误: ${err.message}`)
    }
  }, 1000)  // 延迟1秒确保窗口完全加载
})

app.on('window-all-closed', () => {
  // 关闭Python进程
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill('SIGTERM')
  }
  
  // 关闭本地服务器
  if (localServer) {
    localServer.close()
  }

  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  // 应用退出前关闭Python进程
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill('SIGTERM')
  }
  
  // 关闭本地服务器
  if (localServer) {
    localServer.close()
  }
})
