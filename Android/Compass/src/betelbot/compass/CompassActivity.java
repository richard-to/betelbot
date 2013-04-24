package betelbot.compass;

import android.os.Bundle;
import android.os.Handler;
import android.app.Activity;
import android.widget.TextView;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;

public class CompassActivity extends Activity implements SensorEventListener {

	public static final int PORT = 8888;
	public static final int NUM_READINGS = 10;
	
	private ServerSocket serverSocket;
	private Handler handler = new Handler();	   
	private SensorManager sensorManager;
	private TextView label;
	private float azimuth = 0;	
	private int currentReading = 0;
	private float[] lastXAzimuth = new float[NUM_READINGS];	
	
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_compass);
        label = (TextView)findViewById(R.id.compassLabel);
        sensorManager = (SensorManager)getSystemService(SENSOR_SERVICE);
        Thread server = new Thread(new ServerThread());
        server.start();
    }
    
    @Override
    protected void onResume() {
    	super.onResume();
    	sensorManager.registerListener(this,
    			sensorManager.getDefaultSensor(Sensor.TYPE_ORIENTATION),
    			SensorManager.SENSOR_DELAY_NORMAL);
    }
    
    @Override
    protected void onPause() {
    	super.onPause();
    	sensorManager.unregisterListener(this);
    }
    
    @Override
    protected void onStop() {
    	super.onStop();
    	try {
			serverSocket.close();
		} catch (IOException e) {
			e.printStackTrace();
		}
    }
    
	@Override
	public void onAccuracyChanged(Sensor arg0, int arg1) {}


	@Override
	public void onSensorChanged(SensorEvent arg0) {
		azimuth = arg0.values[0];
		label.setText(String.valueOf(azimuth));		
		lastXAzimuth[currentReading] = azimuth;
		currentReading = (currentReading + 1) % NUM_READINGS;		
	}
	
	public float getAvgAzimuth(float[] readings) {
		float total = 0;
		float avg = 0;
		int length = readings.length;
		for (int i = 0; i < length; i++) {
			total += readings[i];
		}
		if (total > 0) {
			avg = total / length;
		}
		return avg;
	}
	
	public class ServerThread implements Runnable {
		public void run() {
			try {
				serverSocket = new ServerSocket(PORT);
				while (true) {
					Socket client = serverSocket.accept();
					float[] lastXAzimithCopy = lastXAzimuth.clone();
					PrintWriter out = new PrintWriter(
							new BufferedWriter(new OutputStreamWriter(client.getOutputStream())), true);
					out.print(getAvgAzimuth(lastXAzimithCopy));
					client.close();
                    handler.post(new Runnable() {
                        @Override
                        public void run() {                       	
                            label.setText("CONNECTED");
                        }
                    });					
					
				}
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
	}
}

