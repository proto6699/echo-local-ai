#!/usr/bin/env bash
echo "== live/development separation =="
echo
echo "Live service ExecStart:"
systemctl --user cat neco-idle.service 2>/dev/null | grep ExecStart || true
echo
echo "Dev repo: $(cd "$(dirname "$0")/.." && pwd)"
echo
echo "Live service SHOULD reference:  $HOME/neco-idle/neco_monologue.py"
echo "Live service SHOULD NOT match:  $HOME/Projects/echo-local-ai"
echo
echo "Listening on :3000 (live Den):"
(ss -ltnp 2>/dev/null | grep ':3000' || echo "  (nothing)")
echo
echo "Listening on :3001 (test):"
(ss -ltnp 2>/dev/null | grep ':3001' || echo "  (nothing)")
