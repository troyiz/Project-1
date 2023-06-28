from flask import Flask, render_template, request, flash, redirect
import mysql.connector
from datetime import datetime
import MeCab
import openai

app = Flask(__name__)
app.secret_key = "your key"

openai.api_key = "your key"


db = mysql.connector.connect(
    host="your server", user="user", password="your host", database="your diary"
)

cursor = db.cursor()

mecab = MeCab.Tagger("-d /var/lib/mecab/dic/unidic")


@app.route("/")
def index():
    return render_template("index.html")


def get_meishi(document, stopwords):
    meishi = []
    node = mecab.parseToNode(document).next
    stopwords = stopwords
    while node:
        nodeFeature = node.feature.split(",")
        if nodeFeature[0] == "名詞":
            node_surface = node.surface
            if node_surface not in stopwords:
                meishi.append(node_surface)
        node = node.next
    return meishi


def get_doushi(document, stopwords):
    doushi = []
    node = mecab.parseToNode(document).next
    stopwords = stopwords
    while node:
        nodeFeature = node.feature.split(",")
        if nodeFeature[0] == "動詞":
            node_surface = node.surface
            if node_surface not in stopwords:
                doushi.append(node_surface)
        node = node.next
    return doushi


stop_words = [
    "で",
    "？",
    "も",
    "は",
    "か",
    "た",
    "て",
    "の",
    "し",
    "だ",
    "よ",
    "０",
    "ん",
    "な",
    "！",
    "…",
    "ー",
    "に",
    "お",
    "ぜ",
    "ここ",
    "こと",
    "は",
    "ーーー",
]


@app.route("/write", methods=["GET", "POST"])
def write():
    if request.method == "POST":
        question1 = request.form["question1"]
        question2 = request.form["question2"]
        question3 = request.form["question3"]
        answer1 = request.form["answer1"]
        answer2 = request.form["answer2"]
        answer3 = request.form["answer3"]

        # Perform morphological analysis using MeCab
        mecab = MeCab.Tagger("-d /var/lib/mecab/dic/unidic")
        answer1_morphs = "/".join(
            token.split("\t")[0]
            for token in mecab.parse(answer1).strip().split("\n")[:-2]
        )
        answer2_morphs = "/".join(
            token.split("\t")[0]
            for token in mecab.parse(answer2).strip().split("\n")[:-2]
        )
        answer3_morphs = "/".join(
            token.split("\t")[0]
            for token in mecab.parse(answer3).strip().split("\n")[:-2]
        )

        # 명사 추출
        a1_nouns = get_meishi(answer1, stop_words)
        a1_nouns_str = " ".join(a1_nouns)

        a2_nouns = get_meishi(answer2, stop_words)
        a2_nouns_str = " ".join(a2_nouns)

        a3_nouns = get_meishi(answer3, stop_words)
        a3_nouns_str = " ".join(a3_nouns)

        food = ""
        person = ""
        place = ""

        # chatGpt
        for i in range(len(a1_nouns)):
            prompt = "「" + a1_nouns[i] + "」" + "が食べ物の名前なら１を出力、なければ0を出力。"

            response = openai.Completion.create(
                model="text-davinci-003", prompt=prompt, temperature=1, max_tokens=400
            )

            print(str(response["choices"][0]["text"]).strip())

            if str(response["choices"][0]["text"]).strip() == "1":
                food = a1_nouns[i]
                print("what = " + food)

        for j in range(len(a1_nouns)):
            prompt = "「" + a1_nouns[j] + "」" + "が人物の意味なら1を出力してくれ、なければ0を出力してくれ。"

            print(prompt)

            response = openai.Completion.create(
                model="text-davinci-003", prompt=prompt, temperature=1, max_tokens=400
            )

            print(str(response["choices"][0]["text"]).strip())

            if str(response["choices"][0]["text"]).strip() == "1":
                person = a1_nouns[j]
                print("who = " + person)

        for k in range(len(a2_nouns)):
            prompt = "「" + a2_nouns[k] + "」" + "が場所の意味なら1を出力してくれ、なければ0を出力してくれ。"

            print(prompt)

            response = openai.Completion.create(
                model="text-davinci-003", prompt=prompt, temperature=1, max_tokens=400
            )

            print(str(response["choices"][0]["text"]).strip())

            if str(response["choices"][0]["text"]).strip() == "1":
                place = a2_nouns[k]
                print("where = " + place)

        print("food = " + food)
        print("person = " + person)
        print("place = " + place)

        query = "INSERT INTO d_i (Q1, Q2, Q3, A1, A2, A3, A1_morphs, A2_morphs, A3_morphs, food, person, place) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (
            question1,
            question2,
            question3,
            answer1,
            answer2,
            answer3,
            answer1_morphs,
            answer2_morphs,
            answer3_morphs,
            food,
            person,
            place,
        )

        cursor.execute(query, values)
        db.commit()

        flash("日記が正常に保存されました", "success")
        return redirect("/")
    else:
        return render_template("write.html")


@app.route("/view")
def view():
    query = "SELECT * FROM d_i"
    cursor.execute(query)
    data = cursor.fetchall()
    return render_template("view.html", data=data)


@app.route("/view_info/<int:did>/<qn>")
def view_info(did, qn):
    query = "SELECT * FROM d_i WHERE did = %s"
    values = (did,)
    cursor.execute(query, values)
    data = cursor.fetchall()
    return render_template("view_info.html", data=data)


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        # Get the user's answer
        user_answer = request.form["answer"]

        # Retrieve a random food and its creation date from the database
        cursor.execute(
            "SELECT food, place, person, d_date FROM d_i ORDER BY RAND() LIMIT 1"
        )
        result = cursor.fetchone()

        # Get the correct answers for the retrieved food
        correct_place = result[1]
        correct_person = result[2]

        # Check the user's answer against the correct answers
        if correct_place in user_answer and correct_person in user_answer:
            result_message = "覚えていますね。"
            result_class = "success"
        elif "食べ" not in user_answer:
            result_message = "作成したものと違って覚えていらっしゃいますね。"
            result_class = "danger"
        else:
            u_nouns = get_meishi(user_answer, stop_words)
            A_Who = "0"
            A_Where = "0"
            for noun in u_nouns:
                prompt = "「" + noun + "」" + "が人を意味する単語なら１を出力、なければ0を出力。"
                response = openai.Completion.create(
                    model="text-davinci-003",
                    prompt=prompt,
                    temperature=1,
                    max_tokens=4000,
                )
                if str(response["choices"][0]["text"]).strip() == "1":
                    A_Who = noun
                    break

            for noun in u_nouns:
                prompt = "「" + noun + "」" + "が場所を意味する単語なら１を出力、なければ0を出力。"
                response = openai.Completion.create(
                    model="text-davinci-003",
                    prompt=prompt,
                    temperature=1,
                    max_tokens=4000,
                )
                if str(response["choices"][0]["text"]).strip() == "1":
                    A_Where = noun
                    break

            if A_Where != "0" and A_Who != "0":
                result_message = "少し覚えてますね。"
                result_class = "danger"
            else:
                result_message = "覚えていませんね。"
                result_class = "danger"

        # Extract the creation date of the retrieved food
        d_date = result[3].strftime("%Y-%m-%d %H:%M:%S")

        # Render the quiz page with the result message, class, food, and creation date
        return render_template(
            "quiz.html",
            result_message=result_message,
            result_class=result_class,
            food=result[0],
            d_date=d_date,
        )
    else:
        # Retrieve a random food and its creation date from the database
        cursor.execute(
            "SELECT food, place, person, d_date FROM d_i ORDER BY RAND() LIMIT 1"
        )
        result = cursor.fetchone()

        # Extract the creation date of the retrieved food
        d_date = result[3].strftime("%m-%d")

        # Render the quiz page with the random food and creation date
        return render_template("quiz.html", food=result[0], d_date=d_date)


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
