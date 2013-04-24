package betelbot.compass;

import android.os.Bundle;
import android.app.Activity;
import android.widget.TextView;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

public class CompassActivity extends Activity implements SensorEventListener {

	private SensorManager sensorManager;
	private TextView label;
	private float azimuth;
	
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_compass);
        label = (TextView)findViewById(R.id.compassLabel);
        sensorManager = (SensorManager)getSystemService(SENSOR_SERVICE);
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
	public void onAccuracyChanged(Sensor arg0, int arg1) {}


	@Override
	public void onSensorChanged(SensorEvent arg0) {
		azimuth = arg0.values[0];
		label.setText(String.valueOf(azimuth));
	}
}
