"""
Flask Application Entry Point
"""
import sys
import os

# 统一配置：禁用输出缓冲，确保所有 print 立即刷新
# 方案1: 设置环境变量（对所有新创建的流有效）
os.environ['PYTHONUNBUFFERED'] = '1'

# 方案2: 直接重新配置标准输出流（对当前进程立即生效）
if hasattr(sys.stdout, 'reconfigure'):
    # Python 3.7+
    sys.stdout.reconfigure(line_buffering=True)
else:
    # Python 3.6 及更早版本
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

from app import create_app
from app.config.model_config import get_int_config, get_bool_config

# Create application instance
app = create_app()


if __name__ == '__main__':
    port = get_int_config('PORT', 5000)
    debug = get_bool_config('FLASK_DEBUG', True)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False
    )
