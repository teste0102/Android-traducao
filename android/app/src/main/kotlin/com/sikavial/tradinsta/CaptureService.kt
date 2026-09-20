package com.sikavial.tradinsta

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.media.*
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File

/**
 * Serviço em primeiro plano que:
 *  - captura o áudio de OUTROS apps (AudioPlaybackCapture, Android 10+)
 *  - mostra um botão flutuante (Gravar / Parar+Dublar / Tocar)
 *  - envia o WAV pro servidor /dublar e toca a dublagem PT
 *
 * FASE 1 (este arquivo): captura + envio + reprodução manual.
 * FASE 2 (depois de a tradução funcionar): auto-mute do Instagram e sincronia
 * automática por impressão digital de áudio.
 */
class CaptureService : Service() {

    companion object {
        const val ACTION_START = "start"
        const val EXTRA_CODE = "code"
        const val EXTRA_DATA = "data"
        const val EXTRA_URL = "url"
        private const val CH = "traducao_instagram"
        private const val SR = 16000
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var projection: MediaProjection? = null
    private var record: AudioRecord? = null
    private var recording = false
    private var pcm = ByteArrayOutputStream()
    private var serverUrl = "http://192.168.15.11:7900"
    private var lastDub: File? = null

    private lateinit var wm: WindowManager
    private var overlay: View? = null
    private lateinit var status: TextView
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(300, java.util.concurrent.TimeUnit.SECONDS).build()

    override fun onBind(i: Intent?) = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_START) {
            serverUrl = intent.getStringExtra(EXTRA_URL) ?: serverUrl
            startForeground(1, notif())
            val code = intent.getIntExtra(EXTRA_CODE, Activity.RESULT_CANCELED)
            val data = intent.getParcelableExtra<Intent>(EXTRA_DATA)
            val mgr = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = if (data != null) mgr.getMediaProjection(code, data) else null
            showOverlay()
        }
        return START_STICKY
    }

    // ---------- captura ----------
    @Suppress("MissingPermission")
    private fun startRecording() {
        val proj = projection ?: run { toast("Sem permissão de captura"); return }
        val cfg = AudioPlaybackCaptureConfiguration.Builder(proj)
            .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
            .addMatchingUsage(AudioAttributes.USAGE_GAME)
            .build()
        val fmt = AudioFormat.Builder()
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(SR)
            .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
            .build()
        val minBuf = AudioRecord.getMinBufferSize(SR,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        record = AudioRecord.Builder()
            .setAudioFormat(fmt)
            .setBufferSizeInBytes(minBuf * 2)
            .setAudioPlaybackCaptureConfig(cfg)
            .build()
        pcm = ByteArrayOutputStream()
        record?.startRecording()
        recording = true
        status.text = "● Gravando o áudio do vídeo…"
        scope.launch {
            val buf = ByteArray(minBuf)
            while (recording) {
                val n = record?.read(buf, 0, buf.size) ?: 0
                if (n > 0) synchronized(pcm) { pcm.write(buf, 0, n) }
            }
        }
    }

    private fun stopAndSend() {
        if (!recording) { toast("Grave primeiro"); return }
        recording = false
        record?.stop(); record?.release(); record = null
        val bytes = synchronized(pcm) { pcm.toByteArray() }
        if (bytes.size < SR) { status.text = "Áudio curto demais"; return }
        status.text = "Enviando pro servidor…"
        scope.launch {
            try {
                val wav = File(cacheDir, "cap.wav")
                writeWav(wav, bytes, SR)
                val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                    .addFormDataPart("file", "cap.wav",
                        wav.asRequestBody("audio/wav".toMediaType()))
                    .build()
                val req = Request.Builder().url("$serverUrl/dublar").post(body).build()
                http.newCall(req).execute().use { r ->
                    val txt = r.body?.string() ?: ""
                    if (!r.isSuccessful) { ui { status.text = "Erro ${r.code}" }; return@use }
                    val j = JSONObject(txt)
                    val audioUrl = serverUrl + j.getString("audio_url")
                    val dub = File(cacheDir, "dub.mp3")
                    http.newCall(Request.Builder().url(audioUrl).build()).execute().use { a ->
                        dub.outputStream().use { it.write(a.body!!.bytes()) }
                    }
                    lastDub = dub
                    ui { status.text = "Pronto ✅ toque ▶ e dê play no vídeo" }
                }
            } catch (e: Exception) {
                ui { status.text = "Falha: ${e.message}" }
            }
        }
    }

    // ---------- reprodução ----------
    private fun playDub() {
        val f = lastDub ?: run { toast("Nada pra tocar ainda"); return }
        val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        // abaixa o volume de mídia (Instagram) enquanto toca a dublagem
        val vol = am.getStreamVolume(AudioManager.STREAM_MUSIC)
        am.setStreamVolume(AudioManager.STREAM_MUSIC,
            (am.getStreamMaxVolume(AudioManager.STREAM_MUSIC) * 0.15).toInt(), 0)
        val mp = MediaPlayer().apply {
            setAudioAttributes(AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANT)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            setDataSource(f.absolutePath)
            setOnCompletionListener {
                am.setStreamVolume(AudioManager.STREAM_MUSIC, vol, 0)
                it.release()
            }
            prepare(); start()
        }
        status.text = "▶ Tocando dublagem…"
    }

    // ---------- overlay ----------
    private fun showOverlay() {
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        overlay = LayoutInflater.from(this).inflate(R.layout.overlay, null)
        status = overlay!!.findViewById(R.id.ovStatus)
        overlay!!.findViewById<Button>(R.id.ovRec).setOnClickListener { startRecording() }
        overlay!!.findViewById<Button>(R.id.ovStop).setOnClickListener { stopAndSend() }
        overlay!!.findViewById<Button>(R.id.ovPlay).setOnClickListener { playDub() }
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT)
        lp.gravity = Gravity.TOP or Gravity.END
        lp.y = 200
        wm.addView(overlay, lp)
    }

    // ---------- util ----------
    private fun writeWav(f: File, pcm: ByteArray, sr: Int) {
        val n = pcm.size
        val out = f.outputStream()
        fun i32(v: Int) = byteArrayOf((v and 0xff).toByte(), (v shr 8 and 0xff).toByte(),
            (v shr 16 and 0xff).toByte(), (v shr 24 and 0xff).toByte())
        fun i16(v: Int) = byteArrayOf((v and 0xff).toByte(), (v shr 8 and 0xff).toByte())
        out.write("RIFF".toByteArray()); out.write(i32(36 + n)); out.write("WAVE".toByteArray())
        out.write("fmt ".toByteArray()); out.write(i32(16)); out.write(i16(1)); out.write(i16(1))
        out.write(i32(sr)); out.write(i32(sr * 2)); out.write(i16(2)); out.write(i16(16))
        out.write("data".toByteArray()); out.write(i32(n)); out.write(pcm); out.close()
    }

    private fun notif(): Notification {
        val nm = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            nm.createNotificationChannel(NotificationChannel(CH, "Tradução Instagram",
                NotificationManager.IMPORTANCE_LOW))
        return Notification.Builder(this, CH)
            .setContentTitle("Tradução do Instagram")
            .setContentText("Pronto pra capturar e dublar")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).build()
    }

    private fun ui(block: () -> Unit) = Handler(Looper.getMainLooper()).post(block)
    private fun toast(m: String) = ui { Toast.makeText(this, m, Toast.LENGTH_SHORT).show() }

    override fun onDestroy() {
        recording = false
        record?.release()
        projection?.stop()
        overlay?.let { runCatching { wm.removeView(it) } }
        scope.cancel()
        super.onDestroy()
    }
}
