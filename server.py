import http.server
import socketserver
import os


PORT = 8000
DIRECTORY = "./web/" 


class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    # Override the default index files
    index_pages = [
        'basestations.html'
    ]

    def translate_path(self, path):
        path = super().translate_path(path)
        if os.path.isdir(path):
            for index in self.index_pages:
                index_path = os.path.join(path, index)
                if os.path.isfile(index_path):
                    return index_path
                
        return path


os.chdir(DIRECTORY)

Handler = SimpleHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at port http://localhost:{PORT}/ from {DIRECTORY}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
