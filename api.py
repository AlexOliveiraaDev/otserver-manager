from datetime import datetime
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import psutil
from config import *
import config
from log import logger

class FlaskAPI:
    def __init__(self, app_instance):
        self.app_instance = app_instance
        self.flask_app = Flask(__name__)
        CORS(self.flask_app)
        self.setup_routes()
        
    def setup_routes(self):
        
        
        @self.flask_app.route('/api/status', methods=['GET'])
        def get_status():
            try:
                return jsonify({
                    'timestamp': datetime.now().isoformat(),
                    'total_accounts': len(self.app_instance.contas),
                    'open_accounts': self.app_instance.instancias_abertas,
                    'crashed_accounts': self.app_instance.instancias_crashed,
                    'operation_in_progress': self.app_instance.operacao_em_andamento,
                    'current_status': self.app_instance.status_atual,
                    'auto_restart_enabled': AUTO_RESTART_ENABLED,
                    'auto_restart_delay': AUTO_RESTART_DELAY,
                    'ocr_enabled': config.OCR_ENABLED,
                    'ocr_update_interval': OCR_UPDATE_INTERVAL,
                    'accounts': [conta.get_status_info() for conta in self.app_instance.contas]
                })
            except Exception as e:
                logger.error(f"Erro ao obter status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>/stats', methods=['GET'])
        def get_account_stats(login):
            try:
                conta = self._find_account_by_login(login)
                if not conta:
                    return jsonify({'error': 'Conta não encontrada'}), 404
                
                if not config.OCR_ENABLED or not conta.ocr:
                    return jsonify({'error': 'OCR não está habilitado'}), 400
                
                if conta.status != 'aberta':
                    return jsonify({'error': 'Conta não está aberta'}), 400
                
                conta.update_game_stats()
                
                return jsonify({
                    'login': login,
                    'stats': conta.game_stats.to_dict(),
                    'last_update': conta.last_ocr_update.isoformat() if conta.last_ocr_update else None
                })
            except Exception as e:
                logger.error(f"Erro ao obter stats da conta {login}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>/refresh-stats', methods=['POST'])
        def refresh_account_stats(login):
            try:
                conta = self._find_account_by_login(login)
                if not conta:
                    return jsonify({'error': 'Conta não encontrada'}), 404
                
                if not config.OCR_ENABLED or not conta.ocr:
                    return jsonify({'error': 'OCR não está habilitado'}), 400
                
                if conta.status != 'aberta':
                    return jsonify({'error': 'Conta não está aberta'}), 400
                
                conta.last_ocr_update = None
                conta.update_game_stats()
                
                return jsonify({
                    'message': f'Estatísticas atualizadas para {login}',
                    'stats': conta.game_stats.to_dict(),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Erro ao atualizar stats da conta {login}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/all-stats', methods=['GET'])
        def get_all_stats():
            try:
                all_stats = {}
                for conta in self.app_instance.contas:
                    if conta.status == 'aberta' and config.OCR_ENABLED and conta.ocr:
                        conta.update_game_stats()
                        all_stats[conta.login] = {
                            'stats': conta.game_stats.to_dict(),
                            'last_update': conta.last_ocr_update.isoformat() if conta.last_ocr_update else None
                        }
                
                return jsonify({
                    'timestamp': datetime.now().isoformat(),
                    'accounts_stats': all_stats,
                    'total_accounts': len(all_stats)
                })
            except Exception as e:
                logger.error(f"Erro ao obter todas as estatísticas: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts', methods=['GET'])
        def get_accounts():
            try:
                return jsonify([conta.get_status_info() for conta in self.app_instance.contas])
            except Exception as e:
                logger.error(f"Erro ao obter contas: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>', methods=['GET'])
        def get_account(login):
            try:
                conta = self._find_account_by_login(login)
                if conta:
                    return jsonify(conta.get_status_info())
                return jsonify({'error': 'Conta não encontrada'}), 404
            except Exception as e:
                logger.error(f"Erro ao obter conta {login}: {e}")
                return jsonify({'error': str(e)}), 500


        @self.flask_app.route('/api/start-all', methods=['POST'])
        def start_all():
            try:
                if self.app_instance.operacao_em_andamento:
                    return jsonify({'error': 'Operação já em andamento'}), 400
                
                threading.Thread(target=self.app_instance.iniciar_todas, daemon=True).start()
                return jsonify({'message': 'Iniciando todas as contas'})
            except Exception as e:
                logger.error(f"Erro ao iniciar todas as contas: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/stop-all', methods=['POST'])
        def stop_all():
            try:
                self.app_instance.fechar_todas()
                return jsonify({'message': 'Todas as contas foram fechadas'})
            except Exception as e:
                logger.error(f"Erro ao fechar todas as contas: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/restart-crashed', methods=['POST'])
        def restart_crashed():
            try:
                self.app_instance.reiniciar_crashed()
                return jsonify({'message': 'Reiniciando contas crashed'})
            except Exception as e:
                logger.error(f"Erro ao reiniciar contas crashed: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>/start', methods=['POST'])
        def start_account(login):
            try:
                conta = self._find_account_by_login(login)
                if not conta:
                    return jsonify({'error': 'Conta não encontrada'}), 404
                
                if conta.status == 'aberta':
                    return jsonify({'error': 'Conta já está aberta'}), 400
                
                threading.Thread(target=self.app_instance.toggle_conta, args=(conta,), daemon=True).start()
                return jsonify({'message': f'Iniciando conta {login}'})
            except Exception as e:
                logger.error(f"Erro ao iniciar conta {login}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>/stop', methods=['POST'])
        def stop_account(login):
            try:
                conta = self._find_account_by_login(login)
                if not conta:
                    return jsonify({'error': 'Conta não encontrada'}), 404
                
                if conta.status != 'aberta':
                    return jsonify({'error': 'Conta não está aberta'}), 400
                
                threading.Thread(target=self.app_instance.toggle_conta, args=(conta,), daemon=True).start()
                return jsonify({'message': f'Parando conta {login}'})
            except Exception as e:
                logger.error(f"Erro ao parar conta {login}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/accounts/<login>/show', methods=['POST'])
        def show_account(login):
            try:
                conta = self._find_account_by_login(login)
                if not conta:
                    return jsonify({'error': 'Conta não encontrada'}), 404
                
                if conta.status != 'aberta':
                    return jsonify({'error': 'Conta não está aberta'}), 400
                
                conta.mostrar()
                return jsonify({'message': f'Mostrando janela da conta {login}'})
            except Exception as e:
                logger.error(f"Erro ao mostrar conta {login}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/config', methods=['GET'])
        def get_config():
            try:
                return jsonify({
                    'auto_restart_enabled': AUTO_RESTART_ENABLED,
                    'auto_restart_delay': AUTO_RESTART_DELAY,
                    'delay_inicial': DELAY_INICIAL,
                    'delay_final': DELAY_FINAL,
                    'api_port': API_PORT,
                    'ocr_enabled': config.OCR_ENABLED,
                    'ocr_update_interval': OCR_UPDATE_INTERVAL
                })
            except Exception as e:
                logger.error(f"Erro ao obter configuração: {e}")
                return jsonify({'error': str(e)}), 500

        @self.flask_app.route('/api/system-info', methods=['GET'])
        def get_system_info():
            try:
                import platform
                
                return jsonify({
                    'platform': platform.system(),
                    'platform_version': platform.version(),
                    'python_version': platform.python_version(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory': {
                        'total': psutil.virtual_memory().total,
                        'available': psutil.virtual_memory().available,
                        'percent': psutil.virtual_memory().percent
                    },
                    'uptime': datetime.now().isoformat(),
                    'total_processes': len(list(psutil.process_iter())),
                    'ocr_status': {
                        'enabled': config.OCR_ENABLED,
                        'update_interval': OCR_UPDATE_INTERVAL,
                        'active_sessions': sum(1 for conta in self.app_instance.contas 
                                             if conta.status == 'aberta' and conta.ocr is not None)
                    }
                })
            except Exception as e:
                logger.error(f"Erro ao obter informações do sistema: {e}")
                return jsonify({'error': str(e)}), 500

    def _find_account_by_login(self, login):
        
        for conta in self.app_instance.contas:
            if conta.login == login:
                return conta
        return None

    def run(self, host='0.0.0.0', port=None, debug=False):
        
        if port is None:
            port = API_PORT
        
        logger.info(f"Iniciando API Flask em http://{host}:{port}")
        self.flask_app.run(host=host, port=port, debug=debug, threaded=True)