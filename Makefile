.PHONY: help setup debug ui clean kill logs test

help:
	@echo "MQTT Server & Monitor 便捷命令"
	@echo ""
	@echo "make setup         - 一键自动调试设置"
	@echo "make ui            - 启动 Streamlit UI (localhost:8501)"
	@echo "make logs          - 查看 MQTT Server 日志"
	@echo "make test          - 运行集成测试"
	@echo "make kill          - 停止 mosquitto 进程"
	@echo "make clean         - 清理生成的文件"
	@echo ""

setup:
	python debug_setup.py

ui:
	python -m streamlit run ui_app.py

logs:
	tail -f .mqtt_server/mosquitto.log

test:
	python -m pytest -v 2>/dev/null || python -c \
		"from debug_setup import *; print('请先运行: make setup')"

kill:
	pkill -9 mosquitto || true

clean:
	rm -rf .mqtt_server/*.log
	rm -rf .mqtt_server/mosquitto.conf
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help
