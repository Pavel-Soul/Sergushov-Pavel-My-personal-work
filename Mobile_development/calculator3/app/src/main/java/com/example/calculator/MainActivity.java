package com.example.calculator;

import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private TextView display;
    private StringBuilder currentInput = new StringBuilder();
    private String currentOperator = null;
    private Double firstOperand = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        display = findViewById(R.id.display);

        // Инициализация кнопок цифр
        setupNumberButtons();

        // Инициализация кнопок операций
        setupOperationButtons();

        // Инициализация специальных кнопок
        setupSpecialButtons();
    }

    private void setupNumberButtons() {
        int[] numberButtons = {
                R.id.btn0, R.id.btn1, R.id.btn2, R.id.btn3, R.id.btn4,
                R.id.btn5, R.id.btn6, R.id.btn7, R.id.btn8, R.id.btn9
        };

        for (int buttonId : numberButtons) {
            findViewById(buttonId).setOnClickListener(v -> {
                Button button = (Button) v;
                String number = button.getText().toString();
                currentInput.append(number);
                updateDisplay();
            });
        }

        // Кнопка десятичной точки
        findViewById(R.id.btnDecimal).setOnClickListener(v -> {
            if (!currentInput.toString().contains(".")) {
                if (currentInput.length() == 0) {
                    currentInput.append("0.");
                } else {
                    currentInput.append(".");
                }
                updateDisplay();
            }
        });
    }

    private void setupOperationButtons() {
        // Сложение
        findViewById(R.id.btnAdd).setOnClickListener(v -> setOperator("+"));

        // Вычитание
        findViewById(R.id.btnSubtract).setOnClickListener(v -> setOperator("-"));

        // Умножение
        findViewById(R.id.btnMultiply).setOnClickListener(v -> setOperator("*"));

        // Деление
        findViewById(R.id.btnDivide).setOnClickListener(v -> setOperator("/"));

        // Процент
        findViewById(R.id.btnPercent).setOnClickListener(v -> {
            if (currentInput.length() > 0) {
                double number = Double.parseDouble(currentInput.toString());
                double result = number / 100;
                currentInput.setLength(0);
                currentInput.append(result);
                updateDisplay();
            }
        });

        // Квадратный корень
        findViewById(R.id.btnSqrt).setOnClickListener(v -> {
            if (currentInput.length() > 0) {
                double number = Double.parseDouble(currentInput.toString());
                if (number >= 0) {
                    double result = Math.sqrt(number);
                    currentInput.setLength(0);
                    currentInput.append(removeTrailingZeros(result));
                    updateDisplay();
                } else {
                    display.setText("Ошибка");
                    currentInput.setLength(0);
                }
            }
        });

        // Равно
        findViewById(R.id.btnEquals).setOnClickListener(v -> calculateResult());
    }

    private void setupSpecialButtons() {
        // Очистка
        findViewById(R.id.btnClear).setOnClickListener(v -> clearAll());

        // Backspace
        findViewById(R.id.btnBackspace).setOnClickListener(v -> {
            if (currentInput.length() > 0) {
                currentInput.deleteCharAt(currentInput.length() - 1);
                updateDisplay();
            }
        });
    }

    private void setOperator(String operator) {
        if (currentInput.length() > 0) {
            firstOperand = Double.parseDouble(currentInput.toString());
            currentOperator = operator;
            currentInput.setLength(0);
        }
    }

    private void calculateResult() {
        if (firstOperand != null && currentOperator != null && currentInput.length() > 0) {
            double secondOperand = Double.parseDouble(currentInput.toString());
            Double result = null;

            switch (currentOperator) {
                case "+":
                    result = firstOperand + secondOperand;
                    break;
                case "-":
                    result = firstOperand - secondOperand;
                    break;
                case "*":
                    result = firstOperand * secondOperand;
                    break;
                case "/":
                    result = (secondOperand != 0.0) ? firstOperand / secondOperand : Double.NaN;
                    break;
            }

            if (result != null && !result.isNaN()) {
                currentInput.setLength(0);
                currentInput.append(removeTrailingZeros(result));
                firstOperand = null;
                currentOperator = null;
                updateDisplay();
            } else {
                display.setText("Ошибка");
                clearAll();
            }
        }
    }

    private String removeTrailingZeros(double number) {
        if (number % 1 == 0.0) {
            return String.valueOf((int) number);
        } else {
            return String.valueOf(number);
        }
    }

    private void updateDisplay() {
        display.setText(currentInput.length() == 0 ? "0" : currentInput.toString());
    }

    private void clearAll() {
        currentInput.setLength(0);
        firstOperand = null;
        currentOperator = null;
        updateDisplay();
    }
}