package com.example.myapplication;

import android.os.Bundle;
import android.view.View;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private ImageButton startButton;
    private ImageView dogImage;
    private TextView helloText;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        startButton = findViewById(R.id.startButton);
        dogImage = findViewById(R.id.dogImage);
        helloText = findViewById(R.id.helloText);
    }

    // Метод для кнопки Start
    public void onStartButtonClick(View view) {
        // Скрыть кнопку
        startButton.setVisibility(View.GONE);

        // Показать картинку и текст
        dogImage.setVisibility(View.VISIBLE);
        helloText.setVisibility(View.VISIBLE);
    }
}
