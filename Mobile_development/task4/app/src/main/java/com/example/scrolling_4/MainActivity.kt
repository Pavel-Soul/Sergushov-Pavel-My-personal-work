package com.example.scrolling_4


import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val poemTextView = findViewById<TextView>(R.id.poemText)

        val poemText = """
            Был у кошки сын приемный —
Не котенок, а щенок,
Очень милый, очень скромный,
Очень ласковый сынок.
 
Без воды и без мочала
Кошка сына умывала;
Вместо губки, вместо мыла
Языком сыночка мыла.
 
Быстро лижет язычок
Шею, спинку и бочок.
Кошка-мать —
Животное
Очень чистоплотное.
 
Но подрос
Сынок приемный,
И теперь он пес
Огромный.
 
Бедной маме не под силу
Мыть лохматого верзилу.
На громадные бока
Не хватает языка.
 
Чтобы вымыть шею сыну,
Надо влезть ему на спину.
— Ох, — вздохнула кошка-мать, —
Трудно сына умывать!
 
Сам плескайся, сам купайся,
Сам без мамы умывайся!
…
Сын купается в реке,
Мама дремлет на песке.
        """.trimIndent()

        poemTextView.text = poemText
    }
}
