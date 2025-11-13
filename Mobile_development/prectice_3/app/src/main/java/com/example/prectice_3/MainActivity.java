package com.example.prectice_3;

import androidx.appcompat.app.AppCompatActivity;
import android.os.Bundle;
import android.widget.Button;
import android.widget.Toast;

public class MainActivity extends AppCompatActivity {

    Button photoBtn, projectBtn, achieveBtn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        photoBtn = findViewById(R.id.photoBtn);
        projectBtn = findViewById(R.id.projectBtn);
        achieveBtn = findViewById(R.id.achieveBtn);

        photoBtn.setOnClickListener(v ->
                Toast.makeText(this, "Открыт раздел Фото", Toast.LENGTH_SHORT).show()
        );
        projectBtn.setOnClickListener(v ->
                Toast.makeText(this, "Открыт раздел Проекты", Toast.LENGTH_SHORT).show()
        );
        achieveBtn.setOnClickListener(v ->
                Toast.makeText(this, "Открыт раздел Достижения", Toast.LENGTH_SHORT).show()
        );
    }
}
