# App Android — Tradução do Instagram (FASE 1)

App do Samsung S22 (Android 10+) que captura o áudio de outro app (o vídeo do
Instagram), envia pro servidor `/dublar` e toca a dublagem em português.

## O que já faz (fase 1)
- Captura o áudio de mídia de outros apps (MediaProjection + AudioPlaybackCapture)
- Botão flutuante: ● Gravar / ■ Parar + Dublar / ▶ Tocar
- Envia pro servidor e reproduz a dublagem, abaixando o volume da mídia enquanto toca

## O que fica pra fase 2 (após a tradução estar redonda)
- Mutar SÓ o Instagram e sincronizar a dublagem automaticamente no play (fingerprint de áudio)
- Rodar de fora da rede local (via túnel Cloudflare — trocar o endereço no app)

## Como compilar
1. Abrir a pasta `android/` no **Android Studio** (Ladybug ou mais novo).
2. Aguardar o Gradle sincronizar (ele baixa o wrapper e as dependências).
3. Conectar o S22 em modo desenvolvedor (depuração USB) e dar **Run**.
   - Ou gerar APK: menu **Build → Build APK(s)**.

## Como usar
1. Na tela do app: confirme o endereço do servidor (`http://192.168.15.11:7900`) e salve.
2. Toque **1. Permitir botão flutuante** e conceda a permissão.
3. Toque **2. Iniciar captura de áudio** e aceite o pedido de captura de tela/áudio.
4. Abra o Instagram, dê play no vídeo em inglês e toque **● Gravar**.
5. Toque **■ Parar + Dublar** e espere o "Pronto ✅".
6. Dê play no vídeo de novo e toque **▶ Tocar**.

## ⚠️ Ponto que precisa ser testado no aparelho
O Android só deixa capturar o áudio de um app se ele **permitir** captura
(`ALLOW_CAPTURE_BY_ALL`). Se o Instagram bloquear, a gravação vem em silêncio.
Teste isto primeiro — é o único risco que não dá pra prever sem o aparelho.
Se vier mudo: alternativa é capturar pelo microfone com o som no alto-falante,
ou usar a função "compartilhar → salvar vídeo" e mandar o arquivo pro servidor.
