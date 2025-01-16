#!/bin/bash

# 配置文件路径
dir=/app/tools/files/crt/..data
#crt=$dir/server.pem
#key=$dir/server.key
#ca=$dir/ca.crt

# 重载 nginx 的函数
reload_nginx() {
    echo "Files have been modified. Reloading nginx..."
    nginx -s reload
}

# 监控文件变化
monitor_files() {
    # 使用 inotifywait 监控文件更新（包括修改、移动、创建等）
    inotifywait -m -e modify $dir |
    while read -r filename event; do
        echo "Detected change in: $filename"
        reload_nginx
    done
}

# 主程序：后台启动守护进程
start_daemon() {
    # 启动监控进程
    monitor_files &
    echo "File monitoring started. Running in background..."
}

# 如果脚本被直接执行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    start_daemon
fi
