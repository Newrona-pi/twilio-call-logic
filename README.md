# Twilio シリアルコード認証型音声配信サービス

「37card」のような、シリアルコード認証型の電話音声配信サービスのバックエンド実装です。

## 機能

1. ユーザーが電話をかける
2. システムがシリアルコードの入力を求める
3. ユーザーがコードを入力する
4. コードが正しく、かつ「未使用」であれば、そのコードに紐付いた音声を再生し、コードを「使用済み」にする
5. コードが間違っている、または「使用済み」であれば、エラーメッセージを流して切断する

## セットアップ手順

### 1. 必要なライブラリのインストール

```bash
pip install flask twilio
```

または、まとめてインストール：

```bash
pip install -r requirements.txt
```

### 2. シリアルコードの設定

`serial_codes.json` ファイルを編集して、シリアルコードと音声URLを設定します。

```json
{
  "1234": {
    "audio_url": "https://example.com/audio1.mp3",
    "used": false
  },
  "5678": {
    "audio_url": "https://example.com/audio2.mp3",
    "used": false
  }
}
```

- **キー（"1234"など）**: ユーザーが入力するシリアルコード
- **audio_url**: 再生する音声ファイルのURL（MP3形式推奨）
- **used**: 使用済みフラグ（`false`=未使用、`true`=使用済み）

> **注意**: 音声ファイルは、インターネット経由でアクセス可能なURLである必要があります。

### 3. サーバーの起動

```bash
python app.py
```

サーバーが起動すると、`http://localhost:5000` でアクセスできます。

### 4. 外部からアクセス可能にする（ngrok使用例）

ローカル環境で開発する場合、ngrokを使用して外部からアクセス可能にします。

```bash
ngrok http 5000
```

ngrokが生成したURL（例: `https://xxxx-xx-xx-xx-xx.ngrok.io`）をメモしてください。

### 5. Twilio管理画面の設定

1. [Twilio Console](https://console.twilio.com/) にログイン
2. **Phone Numbers** → **Manage** → **Active numbers** から電話番号を選択
3. **Voice Configuration** セクションで以下を設定：
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-domain.com/voice`（ngrokのURLを使用）
   - **HTTP**: POST
4. 設定を保存

## ファイル構成

```
twilio-call-logic/
├── app.py                  # メインのFlaskアプリケーション
├── serial_codes.json       # シリアルコードのデータ
├── README.md              # このファイル
└── requirements.txt       # 必要なライブラリ一覧（オプション）
```

## 編集が必要な箇所

### app.py の編集箇所

コード内の「★ここを編集してください」というコメントがある箇所を、必要に応じて編集してください。

#### 1. データファイルのパス（15行目付近）

```python
DATA_FILE = 'serial_codes.json'
```

#### 2. シリアルコードの桁数（65行目付近）

```python
gather = Gather(
    num_digits=4,  # ★4桁から変更する場合はここを編集
    ...
)
```

#### 3. 案内メッセージのカスタマイズ（72行目付近）

```python
gather.say(
    'こんにちは。シリアルコードを入力してください。',  # ★メッセージを変更
    language='ja-JP'
)
```

#### 4. エラーメッセージのカスタマイズ（114行目、123行目付近）

```python
response.say(
    '入力されたシリアルコードが見つかりません。もう一度確認してください。',
    language='ja-JP'
)
```

#### 5. 成功時のメッセージのカスタマイズ（132行目付近）

```python
response.say(
    '認証に成功しました。音声を再生します。',
    language='ja-JP'
)
```

#### 6. サーバー設定（181行目付近）

```python
app.run(
    host='0.0.0.0',
    port=5000,
    debug=True  # 本番環境では False にしてください
)
```

## テスト方法

### 動作確認

1. サーバーを起動した状態で、設定した電話番号に電話をかける
2. 案内メッセージが流れるので、シリアルコード（例: `1234`）を入力
3. コードが正しければ、音声が再生される
4. もう一度同じコードで電話をかけると、「使用済み」のメッセージが流れる

### デバッグ

サーバーのコンソールに、以下のようなログが出力されます：

```
入力されたコード: 1234
コード 1234 を使用済みにしました
```

## トラブルシューティング

### 音声が再生されない

- `audio_url` が正しいか確認してください
- URLが外部からアクセス可能か確認してください
- 音声ファイルの形式がMP3など対応形式か確認してください

### Twilioから接続できない

- ngrokやサーバーが起動しているか確認してください
- Twilio管理画面のWebhook URLが正しいか確認してください
- HTTPSを使用しているか確認してください（Twilioは基本的にHTTPSが必要）

### データが保存されない

- `serial_codes.json` ファイルへの書き込み権限があるか確認してください
- ファイルのパスが正しいか確認してください

## 本番環境への展開 (Render.com + PostgreSQL)

このアプリケーションを Render.com にデプロイし、PostgreSQLデータベースを使用する手順です。
PostgreSQLを使用することで、再起動してもデータが消えることなく、安全に運用できます。

### デプロイ手順

1. **GitHubへプッシュ**
   このプロジェクトをGitHubのリポジトリにプッシュします。

2. **RenderでPostgreSQLを作成**
   [Render Dashboard](https://dashboard.render.com/) で「New +」→「**PostgreSQL**」を選択します。
   - **Name**: 任意のDB名（例: `twilio-db`）
   - **Database**: 空欄でOK
   - **User**: 空欄でOK
   - **Region**: サーバーと同じリージョン推奨（例: Singapore）
   - **Plan**: Free（無料プランでOK）
   - 「Create Database」をクリック

   完了後、**Internal DB URL**（`postgres://...`）をコピーしておきます。

3. **RenderでWeb Serviceを作成**
   「New +」→「Web Service」を選択します。
   - **Name**: 任意のアプリ名
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

4. **環境変数の設定**
   Web Service作成画面の下部（または作成後の「Environment」タブ）で環境変数を追加します。
   
   - **Key**: `DATABASE_URL`
   - **Value**: 手順2でコピーした **Internal DB URL**

5. **デプロイと初期データ**
   設定完了後、デプロイが始まります。
   
   アプリが初回起動するとき、自動的にデータベースのテーブルが作成され、**`serial_codes.json` の中身が初期データとしてデータベースに登録されます**。
   （※既にデータベースにデータがある場合は登録されません）

### Twilioの設定更新

Renderで発行されたURLを使ってTwilioを設定します。

### Twilioの設定更新

Renderで発行されたURLを使ってTwilioを設定します。

1. **Twilio Consoleにログイン**
   [Twilio Console](https://console.twilio.com/) にアクセスします。

2. **電話番号の設定画面を開く**
   - 左側のサイドメニューから **「Phone Numbers」** > **「Manage」** > **「Active numbers」** をクリックします。
   - ※サイドメニューが見当たらない場合は、画面左上の「Develop」タブをクリックしてみてください。

3. **使用する電話番号を選択**
   - リストから、今回使用する電話番号リンクをクリックします。

4. **Webhookの設定**
   - 設定画面を下の方へスクロールし、**「Voice & Fax」**（または **「Voice Configuration」**）というセクションを探します。
   - **「A CALL COMES IN」** という項目の設定を以下のように変更します：
     - 左のドロップダウン: **Webhook**
     - 右のURL欄: `https://<あなたのアプリ名>.onrender.com/voice`
     - 右端のHTTPメソッド: **HTTP POST**

5. **保存**
   - 画面最下部（または右上）にある **「Save configuration」** ボタンをクリックして設定を保存します。

## ローカルでの開発

ローカル環境（自分のPC）で動かす場合、PostgreSQLは必須ではありません。
環境変数 `DATABASE_URL` が設定されていない場合、自動的に **SQLite** (`local_dev.db`) という簡易データベースファイルが作成され、これを使用します。

```bash
# ローカルで起動
python app.py
```

## ローカルでの開発（ngrok）

## ライセンス

このコードは自由に使用・改変していただけます。

## サポート

問題が発生した場合は、Twilioの公式ドキュメントを参照してください：
- [Twilio Programmable Voice](https://www.twilio.com/docs/voice)
- [TwiML](https://www.twilio.com/docs/voice/twiml)
