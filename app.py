# -*- coding: utf-8 -*-
"""
Twilio Programmable Voice - シリアルコード認証型音声配信サービス
37cardのような電話音声配信システムのバックエンド実装

必要なライブラリ:
    pip install flask twilio

使い方:
    1. serial_codes.json を編集してシリアルコードと音声URLを設定
    2. python app.py でサーバーを起動
    3. Twilio管理画面で、着信時のWebhook URLを設定
       (例: https://your-domain.com/voice)
"""

from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import json
import os

app = Flask(__name__)

from flask import Flask, request, send_from_directory, url_for
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask_sqlalchemy import SQLAlchemy
import json
import os

app = Flask(__name__)

# =============================================================================
# ★ここを編集してください: データベース設定
# =============================================================================
# Renderなどの環境変数 'DATABASE_URL' があればそれを使い、なければローカルのSQLiteを使う
# ※RenderのPostgreSQL URLは 'postgres://' で始まることがありますが、
#   SQLAlchemyでpg8000を使うため 'postgresql+pg8000://' に置換します。
database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_dev.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =============================================================================
# モデル定義 (データベースのテーブル構造)
# =============================================================================
class SerialCode(db.Model):
    __tablename__ = 'serial_codes'
    
    code = db.Column(db.String(20), primary_key=True)
    audio_url = db.Column(db.String(500), nullable=False)
    # used = db.Column(db.Boolean, default=False, nullable=False) # 廃止
    usage_count = db.Column(db.Integer, default=0, nullable=False) # 現在の使用回数
    max_uses = db.Column(db.Integer, default=3, nullable=False)    # 最大使用可能回数

    def __repr__(self):
        return f'<SerialCode {self.code} ({self.usage_count}/{self.max_uses})>'

# JSONファイル（初期データ/シードデータ用）
DATA_FILE = 'serial_codes.json'

def init_db():
    """データベースの初期化とシードデータの投入"""
    with app.app_context():
        # テーブル作成（存在しない場合のみ）
        db.create_all()
        
        try:
            # 試しにクエリを実行して、スキーマが整合しているか確認
            # usage_countカラムがない場合、ここでエラーになるはず
            if SerialCode.query.count() == 0:
                print("データベースが空です。serial_codes.json から初期データを投入します...")
                load_data_from_json()
        except Exception as e:
            # カラム不足などのエラーが出た場合、DBをリセットして再構築する
            print(f"データベースエラー検知 (スキーマ不整合の可能性): {e}")
            print("データベースを再構築します...")
            db.drop_all()
            db.create_all()
            load_data_from_json()
            print("データベースの再構築が完了しました。")

def load_data_from_json():
    """JSONからデータをロードする共通関数"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for code, info in data.items():
            # 既に存在しないか念のため確認
            if not SerialCode.query.get(code):
                new_code = SerialCode(
                    code=code,
                    audio_url=info.get('audio_url'),
                    usage_count=info.get('usage_count', 0),
                    max_uses=info.get('max_uses', 3)
                )
                db.session.add(new_code)
        
        db.session.commit()
        print("初期データの投入が完了しました。")
    else:
        print(f"警告: {DATA_FILE} が見つかりません。")

# アプリ起動時にDB初期化を行う（本番ではコマンドで行うのが一般的だが簡易化のため）
init_db()

from flask import Flask, request, send_from_directory, url_for
# ... (imports)

# ... (db setup)

# ... (init_db function)

# ★追加: 音声ファイルを配信するエンドポイント
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """
    音声ファイルを配信するエンドポイント
    例: /audio/hayase.wav にアクセスすると、ローカルの hayase.wav を返す
    """
    return send_from_directory('.', filename)

@app.route('/voice', methods=['GET', 'POST'])
def voice():
    """
    着信時に呼ばれるエンドポイント
    """
    response = VoiceResponse()
    
    # Gather: ユーザーからの入力（DTMFトーン）を受け付ける
    gather = Gather(
        num_digits=4,           # 入力桁数（★必要に応じて変更してください）
        action='/check_code',   # 入力後に呼ばれるエンドポイント
        method='POST',
        timeout=10              # 入力待ち時間（秒）
    )
    
    # 日本語で案内メッセージを読み上げる
    gather.say(
        'こんにちは。シリアルコードを入力してください。',
        language='ja-JP'
    )
    
    response.append(gather)
    
    # 入力がなかった場合のメッセージ
    response.say(
        '入力が確認できませんでした。もう一度おかけ直しください。',
        language='ja-JP'
    )
    
    return str(response)

@app.route('/check_code', methods=['POST'])
def check_code():
    """
    シリアルコード入力後に呼ばれるエンドポイント
    """
    response = VoiceResponse()
    
    # ユーザーが入力した番号を取得
    digits = request.form.get('Digits', '')
    # 発信者の電話番号を取得 (Twilioからのリクエストに含まれる)
    user_phone_number = request.form.get('From')

    print(f"入力されたコード: {digits}, 発信者番号: {user_phone_number}")
    
    # データベースから検索
    serial_code = SerialCode.query.get(digits)
    
    # シリアルコードの検証
    if not serial_code:
        # コードが存在しない場合
        response.say(
            '入力されたシリアルコードが見つかりません。もう一度確認してください。',
            language='ja-JP'
        )
        response.hangup()
        return str(response)
        
    elif serial_code.usage_count >= serial_code.max_uses:
        # 回数制限に達している場合
        response.say(
            'このシリアルコードは使用回数の上限に達しています。',
            language='ja-JP'
        )
        response.hangup()
        return str(response)
        
    # =============================================================================
    # ★変更点: ここで折り返し電話の処理を行う
    # =============================================================================
    
    # 環境変数からTwilioの認証情報と発信元番号を取得
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')

    if not all([account_sid, auth_token, twilio_number]):
        # 環境変数が設定されていない場合のエラーハンドリング
        print("エラー: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER が設定されていません。")
        response.say('システムエラーが発生しました。管理者に問い合わせてください。', language='ja-JP')
        response.hangup()
        return str(response)

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        # 折り返し時に実行させるTwiMLのURL (新しいエンドポイントを指定)
        # _external=True で絶対URLを生成
        callback_url = url_for('callback_process', code=digits, _external=True)
        
        # プロキシ対策 (Renderなどで http になる場合があるため)
        if request.headers.get('X-Forwarded-Proto') == 'https':
            callback_url = callback_url.replace('http://', 'https://', 1)

        print(f"折り返し発信を開始します: {user_phone_number} -> {callback_url}")

        # 折り返し電話の発信
        call = client.calls.create(
            to=user_phone_number,
            from_=twilio_number,
            url=callback_url
        )

        # 現在の通話に対してアナウンスして切断
        response.say(
            '認証に成功しました。一度電話を切らせていただきます。すぐに折り返しお電話いたしますので、少々お待ちください。',
            language='ja-JP'
        )
        response.hangup()

    except Exception as e:
        print(f"折り返し発信エラー: {e}")
        response.say('電話の発信中にエラーが発生しました。', language='ja-JP')
        response.hangup()

    return str(response)


@app.route('/callback_process/<code>', methods=['POST', 'GET'])
def callback_process(code):
    """
    ★追加: 折り返し電話がつながった後に実行される処理
    ここで音声を再生し、使用済みフラグを更新する
    """
    response = VoiceResponse()
    serial_code = SerialCode.query.get(code)

    if not serial_code:
        response.say('システムエラーです。コード情報が見つかりません。', language='ja-JP')
        response.hangup()
        return str(response)
    
    # 音声ファイルのURL解決ロジック
    audio_target = serial_code.audio_url
    if not audio_target.startswith(('http://', 'https://')):
        # ローカルファイル配信の場合
        audio_url = url_for('serve_audio', filename=audio_target, _external=True)
        if request.headers.get('X-Forwarded-Proto') == 'https':
            audio_url = audio_url.replace('http://', 'https://', 1)
    else:
        audio_url = audio_target
    
    print(f"折り返し通話: 再生URL {audio_url}")

    # 音声を再生
    response.play(audio_url)

    # 終了メッセージ
    response.say(
        'ご利用ありがとうございました。',
        language='ja-JP'
    )
    
    # ★重要: 使用回数をカウントアップ
    if serial_code.usage_count < serial_code.max_uses:
        serial_code.usage_count += 1
        db.session.commit()
        print(f"コード {code} の使用回数を更新: {serial_code.usage_count}/{serial_code.max_uses}")

    return str(response)



@app.route('/admin/reset_code/<code>')
def reset_code(code):
    """
    管理者用: 指定したシリアルコードの使用回数をリセット
    """
    serial_code = SerialCode.query.get(code)
    
    if not serial_code:
        return f'エラー: コード "{code}" は存在しません。', 404
    
    serial_code.usage_count = 0
    db.session.commit()
    
    return f'コード "{code}" をリセットしました（使用回数 0/{serial_code.max_uses}）。'


@app.route('/admin/reset_all')
def reset_all():
    """
    管理者用: すべてのシリアルコードの使用回数をリセット
    """
    updated_count = SerialCode.query.update({'usage_count': 0})
    db.session.commit()
    
    return f'{updated_count}個のコードをリセットしました。'


@app.route('/admin/list_codes')
def list_codes():
    """
    管理者用: データベース内のすべてのシリアルコードを表示
    """
    codes = SerialCode.query.all()
    
    result = '<h1>シリアルコード一覧</h1><table border="1"><tr><th>コード</th><th>音声URL</th><th>使用状況</th></tr>'
    for code in codes:
        result += f'<tr><td>{code.code}</td><td>{code.audio_url}</td><td>{code.usage_count} / {code.max_uses}</td></tr>'
    result += '</table>'
    
    return result


@app.route('/admin/update_from_json')
def update_from_json():
    """
    管理者用: serial_codes.json の内容でデータベースを更新
    """
    if not os.path.exists(DATA_FILE):
        return f'エラー: {DATA_FILE} が見つかりません。', 404
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated = 0
    added = 0
    
    for code, info in data.items():
        serial_code = SerialCode.query.get(code)
        
        if serial_code:
            # 既存のコードを更新
            serial_code.audio_url = info.get('audio_url')
            # max_usesがJSONにあれば更新
            if 'max_uses' in info:
                serial_code.max_uses = info['max_uses']
            updated += 1
        else:
            # 新しいコードを追加
            new_code = SerialCode(
                code=code,
                audio_url=info.get('audio_url'),
                usage_count=info.get('usage_count', 0),
                max_uses=info.get('max_uses', 3)
            )
            db.session.add(new_code)
            added += 1
    
    db.session.commit()
    
    return f'更新完了: {updated}個のコードを更新、{added}個のコードを追加しました。'

@app.route('/admin/init_db_force')
def init_db_force():
    """
    管理者用: データベースを強制的に再作成（初期化）する
    注意: すべてのデータが消去され、serial_codes.jsonの内容で再構築されます。
    スキーマ変更（カラム追加など）があった場合に実行してください。
    """
    db.drop_all()
    init_db()
    return 'データベースを強制初期化しました。新しいスキーマが適用されました。'




@app.route('/')
def index():
    """
    ルートエンドポイント（動作確認用）
    
    ブラウザでアクセスしたときに、サーバーが動いているか確認できます。
    """
    return '''
    <html>
        <head>
            <meta charset="utf-8">
            <title>Twilio Voice Service</title>
        </head>
        <body>
            <h1>Twilio シリアルコード認証型音声配信サービス</h1>
            <p>サーバーは正常に動作しています。</p>
            <p>Twilio管理画面で、着信時のWebhook URLを設定してください。</p>
            <ul>
                <li>Voice URL: <code>/voice</code></li>
            </ul>
        </body>
    </html>
    '''


if __name__ == '__main__':
    # =============================================================================
    # ★ここを編集してください: サーバー設定
    # =============================================================================
    # 本番環境では、debug=False にして、適切なホスト・ポートを設定してください
    # ngrokなどを使用する場合は、このまま localhost:5000 で問題ありません
    app.run(
        host='0.0.0.0',  # 外部からアクセス可能にする場合
        port=5000,       # ポート番号
        debug=True       # 開発時のみTrue、本番では False にしてください
    )
