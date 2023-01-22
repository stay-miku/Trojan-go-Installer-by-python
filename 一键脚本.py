import os

# 记得更新
trojan_download_url = "https://github.com/p4gefau1t/trojan-go/releases/download/v0.10.6/trojan-go-linux-amd64.zip"


def install():
    local_domain = input("vps绑定域名:")

    web = input("是否使用本地web服务器作为伪装网站,不会搭建网站就不使用(Y/n):")
    if web == "y" or web == "":
        print("本地服务器作为伪装网站,将会安装nginx")
        local_web = True
    elif web == "n":
        print("远程服务器作为伪装网站,不会安装本地web服务")
        local_web = False
        remote_ip = input("伪装网站ip地址(需要你自己去找,比如把bing的ip填进去):")
        remote_port = input("伪装网站端口:")
    else:
        print("错误输入")
        return 1

    ws = input("是否启用websocket(用于cdn流量中转,对于垃圾线路提升很高,以及使用负载均衡提速)(Y/n):")
    if ws == "y" or ws == "":
        ws_able = True
        print("启用websocket")
    elif ws == "n":
        ws_able = False
        print("不启用websocket")
    else:
        print("错误输入")
        return 1

    print("下载trojan-go...")
    os.system("wget -P /root -O trojan.zip " + trojan_download_url)
    print("解压压缩包...")
    os.system("mkdir /etc/trojan")

    # 依赖问题
    os.system("apt install unzip -y")
    os.system("apt install curl -y")
    os.system("apt install ufw -y")
    os.system("ufw enable")
    os.system("ufw allow 22")

    os.system("unzip -d /etc/trojan /root/trojan.zip")
    trojan_config = """{
    "run_type": "server",
    "local_addr": "0.0.0.0",
    "local_port": 443,
    "remote_addr": "$remote_ip",
    "remote_port": $remote_port,
    "password": [
        "$password"
    ],
    "ssl": {
        "verify": true,
        "verify_hostname": true,
        "cert": "/etc/trojan/server.crt",
        "key": "/etc/trojan/server.key",
        "sni": "$domain"
    },
    "websocket": {
    "enabled": $ws_able,
    "path": "/$path",
    "host": "$domain"
    }
}"""
    trojan_config = trojan_config.replace("$domain", local_domain)
    if local_web:
        trojan_config = trojan_config.replace("$remote_ip", "127.0.0.1").replace("$remote_port", "80")
    else:
        trojan_config = trojan_config.replace("$remote_ip", remote_ip).replace("$remote_port", remote_port)
    trojan_password = os.popen("openssl rand -base64 20").readline()[:-2]
    trojan_config = trojan_config.replace("$password", trojan_password)
    if ws_able:
        trojan_ws_path = os.popen("openssl rand -base64 10").readline()[:-2]
        trojan_config = trojan_config.replace("$ws_able", "true")
        trojan_config = trojan_config.replace("$path", trojan_ws_path)
    else:
        trojan_config = trojan_config.replace("$ws_able", "false")
        trojan_config = trojan_config.replace("$path", "")

    trojan_config_file = open("/etc/trojan/config.json", "w")
    trojan_config_file.write(trojan_config)
    trojan_config_file.close()
    print("trojan配置完毕")

    print("申请证书...时间可能会比较长,请确保域名解析已生效")
    os.system("ufw allow 80")
    os.system("ufw allow 443")
    os.system("curl https://get.acme.sh | sh")
    os.system("apt install socat")
    os.system("ln -s  /root/.acme.sh/acme.sh /usr/local/bin/acme.sh")
    acme_email = "root@" + local_domain
    os.system("acme.sh --register-account -m $email".replace("$email", acme_email))
    os.system("acme.sh  --issue -d $domain --standalone -k ec-256".replace("$domain", local_domain))
    os.system(
        "acme.sh --installcert -d $domain --ecc --key-file /etc/trojan/server.key  --fullchain-file /etc/trojan/server.crt".replace(
            "$domain", local_domain))
    print("证书安装完毕")

    print("配置service...")
    trojan_service_config = """[Unit]
Description=Trojan-Go
After=network.target nss-lookup.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/etc/trojan/trojan-go -config /etc/trojan/config.json
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target"""
    trojan_service_config_file = open("/etc/systemd/system/trojan.service", "w")
    trojan_service_config_file.write(trojan_service_config)
    trojan_service_config_file.close()
    os.system("systemctl daemon-reload")
    os.system("systemctl enable trojan")
    print("service配置完毕")

    if local_web:
        print("安装nginx...")
        os.system("apt install nginx -y")
        nginx_config = """server {
    listen 80;
    listen [::]:80;

    server_name $domain;

    root /var/www/trojan;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}"""
        nginx_config_file = open("/etc/nginx/sites-enabled/trojan.conf", "w")
        nginx_config_file.write(nginx_config.replace("$domain", local_domain))
        nginx_config_file.close()
        os.system("mkdir /var/www/trojan")
        os.system("systemctl restart nginx")
        print("nginx安装成功,输入systemctl status nginx查看状态")

    os.system("systemctl start trojan")
    print("trojan启动成功,输入systemctl status trojan查看状态,输入systemctl restart trojan重启")

    if ws_able:
        trojan_link = "trojan://$password@$domain:443?security=tls&sni=$domain&type=ws&host=$domain&path=%2F$path#trojan_$domain".replace(
            "$domain", local_domain).replace("$password", trojan_password).replace("$path", trojan_ws_path)
    else:
        trojan_link = "trojan://$password@$domain:443?security=tls&sni=$domain&type=tcp&headerType=none&host=$domain#trojan_$domain".replace(
            "$domain", local_domain).replace("$password", trojan_password)

    print("订阅地址:" + trojan_link)
    if local_web:
        print("网站根目录为:/var/www/trojan,请在该目录下存放网站文件")


install()
