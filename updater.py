import subprocess
import requests
import os
import sys
import zipfile
import shutil
import tempfile
from version import __version__

# Configurações
GITHUB_REPO = "AlexOliveiraaDev/otserver-manager"  # Substitua pelo seu repo
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = __version__

class Updater:
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
    def get_remote_version_and_download_url(self):
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            if response.status_code == 200:
                print(response.json())
                data = response.json()
                version = data['tag_name'].replace('v', '')  # Remove 'v' se houver
                
                # Procura por arquivo .zip nos assets
                download_url = data["zipball_url"]
                
                
                return version, download_url
            return None, None
        except Exception as e:
            print(f"Erro ao verificar versão remota: {e}")
            return None, None
    
    def compare_versions(self, current, remote):
        try:
            current_parts = [int(x) for x in current.split('.')]
            remote_parts = [int(x) for x in remote.split('.')]
            
            # Normaliza tamanhos
            while len(current_parts) < len(remote_parts):
                current_parts.append(0)
            while len(remote_parts) < len(current_parts):
                remote_parts.append(0)
            
            return remote_parts > current_parts
        except:
            return False
    
    def check_for_updates(self):
        """Verifica se há atualizações disponíveis"""
        print("Verificando atualizações...")
        remote_version, _ = self.get_remote_version_and_download_url()
        
        if not remote_version:
            print("Não foi possível verificar atualizações")
            return False
            
        print(f"Versão atual: {CURRENT_VERSION}")
        print(f"Versão disponível: {remote_version}")
        
        return self.compare_versions(CURRENT_VERSION, remote_version)
    
    def download_and_extract(self, download_url):
        """Baixa e extrai a release"""
        try:
            print("Baixando atualização...")
            
            # Baixa o arquivo
            response = requests.get(download_url, stream=True)
            if response.status_code != 200:
                print("Erro ao baixar arquivo")
                return False
            
            # Salva em arquivo temporário
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_zip_path = temp_file.name
            
            print("Extraindo arquivos...")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                extracted_items = os.listdir(temp_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                
                print("Substituindo arquivos...")
                for item in os.listdir(source_dir):
                    print("substituindo " + item)
                    source_path = os.path.join(source_dir, item)
                    dest_path = os.path.join(self.current_dir, item)
                    
                    if os.path.isfile(source_path):
                        shutil.copy2(source_path, dest_path)
                    elif os.path.isdir(source_path):
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(source_path, dest_path)
            
            os.unlink(temp_zip_path)
            
            print("✅ Atualização concluída com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro durante atualização: {e}")
            return False
    
    def update(self):
        """Executa download e extração da release"""
        _, download_url = self.get_remote_version_and_download_url()
        
        if not download_url:
            print("URL de download não encontrada")
            return False
            
        return self.download_and_extract(download_url)
    
    def auto_update(self):
        """Processo completo de verificação e atualização"""
        if self.check_for_updates():
            print("\n🔄 Nova versão disponível!")
            resposta = input("Deseja atualizar agora? (s/n): ").lower().strip()
            
            if resposta in ['s', 'sim', 'y', 'yes']:
                if self.update():
                    input("Pressione Enter para fechar...")
                    sys.exit(0)
                else:
                    print("Falha na atualização. Continuando com versão atual...")
            else:
                print("Atualização cancelada. Continuando com versão atual...")
        else:
            print("✅ Launcher está atualizado!")

def check_updates_on_startup():
    """Função para verificar atualizações na inicialização"""
    updater = Updater()
    updater.auto_update()

if __name__ == "__main__":
    updater = Updater()
    updater.auto_update()