package com.sikavial.tradinsta

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: android.content.SharedPreferences
    private lateinit var projMgr: MediaProjectionManager

    private val projectionLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
            if (res.resultCode == Activity.RESULT_OK && res.data != null) {
                val i = Intent(this, CaptureService::class.java).apply {
                    action = CaptureService.ACTION_START
                    putExtra(CaptureService.EXTRA_CODE, res.resultCode)
                    putExtra(CaptureService.EXTRA_DATA, res.data)
                    putExtra(CaptureService.EXTRA_URL, serverUrl())
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i) else startService(i)
                Toast.makeText(this, "Serviço iniciado. Use o botão flutuante.", Toast.LENGTH_LONG).show()
            } else {
                Toast.makeText(this, "Captura de áudio negada.", Toast.LENGTH_LONG).show()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = getSharedPreferences("cfg", Context.MODE_PRIVATE)
        projMgr = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager

        val url = findViewById<EditText>(R.id.url)
        url.setText(prefs.getString("url", "http://192.168.15.11:7900"))

        findViewById<Button>(R.id.saveUrl).setOnClickListener {
            prefs.edit().putString("url", url.text.toString().trim().trimEnd('/')).apply()
            Toast.makeText(this, "Servidor salvo.", Toast.LENGTH_SHORT).show()
        }

        findViewById<Button>(R.id.overlay).setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")))
            } else Toast.makeText(this, "Sobreposição já permitida.", Toast.LENGTH_SHORT).show()
        }

        findViewById<Button>(R.id.start).setOnClickListener {
            if (!Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "Ative a sobreposição primeiro.", Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }
            projectionLauncher.launch(projMgr.createScreenCaptureIntent())
        }

        findViewById<Button>(R.id.stop).setOnClickListener {
            stopService(Intent(this, CaptureService::class.java))
            Toast.makeText(this, "Serviço parado.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun serverUrl() = prefs.getString("url", "http://192.168.15.11:7900")!!
}
