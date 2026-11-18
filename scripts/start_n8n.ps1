# Khoi dong n8n local cho du an Swallow (chay moi lan mo PowerShell moi).
# Yeu cau: fnm + Node 24 (n8n chua ho tro Node 26), n8n da cai: npm i -g n8n
fnm use 24
$env:N8N_LISTEN_ADDRESS = "127.0.0.1"      # chi nghe localhost
$env:NODES_EXCLUDE = "[]"                   # bat node Execute Command (rui ro: chay lenh tuy y; chi dung may ca nhan, 1 nguoi dung)
$env:N8N_DIAGNOSTICS_ENABLED = "false"      # tat telemetry
n8n start                                   # UI: http://localhost:5678
