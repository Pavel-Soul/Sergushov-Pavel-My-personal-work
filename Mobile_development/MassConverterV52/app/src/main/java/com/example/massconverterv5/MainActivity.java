package com.example.massconverterv5; // Я ИСПРАВИЛ ЭТОТ АДРЕС ПОД ТВОЙ ПРОЕКТ

import androidx.appcompat.app.AppCompatActivity;
import android.os.Bundle;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends AppCompatActivity {

    private EditText inputValue;
    private Spinner unitSpinner;
    private Button calculateButton;
    private TextView resultsTextView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        inputValue = findViewById(R.id.inputValue);
        unitSpinner = findViewById(R.id.unitSpinner);
        calculateButton = findViewById(R.id.calculateButton);
        resultsTextView = findViewById(R.id.resultsTextView);

        setupSpinner();

        calculateButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                calculate();
            }
        });
    }

    private void setupSpinner() {
        ArrayAdapter<CharSequence> adapter = ArrayAdapter.createFromResource(this,
                R.array.mass_units, android.R.layout.simple_spinner_item);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        unitSpinner.setAdapter(adapter);
    }

    private void calculate() {
        String inputText = inputValue.getText().toString();
        if (inputText.isEmpty()) {
            Toast.makeText(this, "Пожалуйста, введите значение", Toast.LENGTH_SHORT).show();
            return;
        }

        double value = Double.parseDouble(inputText);
        String selectedUnit = unitSpinner.getSelectedItem().toString();
        double valueInGrams = 0;

        switch (selectedUnit) {
            case "Караты": valueInGrams = value * 0.2; break;
            case "Граммы": valueInGrams = value; break;
            case "Килограммы": valueInGrams = value * 1000; break;
            case "Центнеры": valueInGrams = value * 100000; break;
            case "Тонны": valueInGrams = value * 1000000; break;
            case "Фунты": valueInGrams = value * 453.592; break;
            case "Унции": valueInGrams = value * 28.3495; break;
        }

        double carats = valueInGrams / 0.2;
        double grams = valueInGrams;
        double kilograms = valueInGrams / 1000;
        double centners = valueInGrams / 100000;
        double tons = valueInGrams / 1000000;
        double pounds = valueInGrams / 453.592;
        double ounces = valueInGrams / 28.3495;

        String results = String.format(
                "Караты: %.4f\n" +
                        "Граммы: %.4f\n" +
                        "Килограммы: %.4f\n" +
                        "Центнеры: %.4f\n" +
                        "Тонны: %.4f\n" +
                        "Фунты: %.4f\n" +
                        "Унции: %.4f",
                carats, grams, kilograms, centners, tons, pounds, ounces
        );

        resultsTextView.setText(results);
    }
}