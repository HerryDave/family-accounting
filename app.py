from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, FloatField
from wtforms.validators import DataRequired, Length, Email, NumberRange, InputRequired

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import argparse

# 加载环境变量
load_dotenv()

# 初始化Flask应用
from flask_wtf.csrf import CSRFProtect
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_for_testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///finance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
csrf = CSRFProtect(app)

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    accounts = db.relationship('Account', backref='user', lazy=True)

# 交易类别模型
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    transactions = db.relationship('Transaction', backref='category', lazy=True)

# 账户模型
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'cash', 'card', 'alipay', 'wechat', etc.
    balance = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='account', lazy=True)

# 家庭成员模型
class FamilyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    relationship = db.Column(db.String(50))  # 例如：'配偶', '子女', '父母'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='family_member', lazy=True)

# 交易记录模型
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    fee_rate = db.Column(db.Float, default=0.0)  # 交易费率百分比
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=True)

# 投资产品模型
class InvestmentProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # 产品代码
    type = db.Column(db.String(20), nullable=False)  # 'money_fund', 'fund', 'stock'
    description = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    holdings = db.relationship('InvestmentHolding', backref='product', lazy=True)
    transactions = db.relationship('InvestmentTransaction', backref='product', lazy=True)

# 投资持仓模型
class InvestmentHolding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account', backref='investment_holdings')
    product_id = db.Column(db.Integer, db.ForeignKey('investment_product.id'), nullable=False)
    quantity = db.Column(db.Float, default=0.0)  # 持有数量
    cost_price = db.Column(db.Float, default=0.0)  # 成本价
    current_price = db.Column(db.Float, default=0.0)  # 当前价
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)  # 关联的资金账户
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 投资交易模型
class InvestmentTransaction(db.Model):
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account', backref='investment_transactions')
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('investment_product.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    fee_rate = db.Column(db.Float, default=0.0)  # 'buy', 'sell', 'redeem'
    quantity = db.Column(db.Float, nullable=False)  # 交易数量
    price = db.Column(db.Float, nullable=False)  # 交易价格
    amount = db.Column(db.Float, nullable=False)  # 交易金额
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_member.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)  # 关联的资金账户
    description = db.Column(db.String(200))

# 创建数据库表
with app.app_context():
    db.create_all()
    # 添加默认类别
    if not Category.query.filter_by(name='工资').first():
        db.session.add(Category(name='工资', type='income'))
        db.session.add(Category(name='投资', type='income'))
        db.session.add(Category(name='餐饮', type='expense'))
        db.session.add(Category(name='交通', type='expense'))
        db.session.add(Category(name='购物', type='expense'))
        db.session.add(Category(name='住房', type='expense'))
        db.session.add(Category(name='娱乐', type='expense'))
        db.session.commit()
    
    # 添加默认管理员用户
    if not User.query.filter_by(username='admin').first():
        admin_password = generate_password_hash('admin')
        admin_user = User(username='admin', email='admin@example.com', password=admin_password)
        db.session.add(admin_user)
        # 创建默认账户
        default_accounts = [
            {'name': '现金', 'type': 'cash', 'balance': 0.0},
            {'name': '支付宝', 'type': 'alipay', 'balance': 0.0},
            {'name': '微信', 'type': 'wechat', 'balance': 0.0}
        ]
        
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            for account_data in default_accounts:
                existing_account = Account.query.filter_by(
                    name=account_data['name'],
                    user_id=admin_user.id
                ).first()
                if not existing_account:
                    new_account = Account(
                        name=account_data['name'],
                        type=account_data['type'],
                        balance=account_data['balance'],
                        user_id=admin_user.id
                    )
                    db.session.add(new_account)
        
        db.session.commit()

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

# 注册表单
class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('注册')

# 账户表单和路由，更新交易处理逻辑以支持账户选择
class AccountForm(FlaskForm):
    name = StringField('账户名称', validators=[DataRequired()])
    type = SelectField('账户类型', validators=[DataRequired()],
                      choices=[('cash', '现金'), ('card', '银行卡'), ('alipay', '支付宝'), ('wechat', '微信支付')])
    balance = StringField('初始余额', validators=[DataRequired()])
    submit = SubmitField('添加')

class TransactionForm(FlaskForm):
    amount = StringField('金额', validators=[DataRequired()])
    description = StringField('描述')
    date = DateField('交易日期', validators=[DataRequired()], format='%Y-%m-%d')
    category = SelectField('类别', validators=[DataRequired()], coerce=str)
    account = SelectField('账户', validators=[DataRequired()], coerce=str)
    family_member = SelectField('家庭成员', coerce=str, choices=[('','请选择家庭成员')])
    submit = SubmitField('添加')

class TransactionFilterForm(FlaskForm):
    start_date = DateField('开始日期', format='%Y-%m-%d')
    end_date = DateField('结束日期', format='%Y-%m-%d')
    category = SelectField('类别', coerce=str, choices=[('all', '所有类别')])
    submit = SubmitField('筛选')

class FamilyMemberForm(FlaskForm):
    name = StringField('成员姓名', validators=[DataRequired()])
    relationship = StringField('与本人关系', validators=[DataRequired()])
    submit = SubmitField('保存')

# 投资产品表单
class InvestmentProductForm(FlaskForm):
    name = StringField('产品名称', validators=[DataRequired()])
    code = StringField('产品代码', validators=[DataRequired()])
    type = SelectField('产品类型', validators=[DataRequired()],
                      choices=[('money_fund', '货币基金'), ('fund', '基金'), ('stock', '股票')])
    description = StringField('产品描述')
    submit = SubmitField('添加')

# 投资交易表单
class InvestmentTransactionForm(FlaskForm):
    product = SelectField('投资产品', validators=[DataRequired()], coerce=int)
    transaction_type = SelectField('交易类型', validators=[DataRequired()],
                                 choices=[('buy', '买入'), ('sell', '卖出')])
    quantity = StringField('数量', validators=[DataRequired()])
    price = StringField('价格', validators=[DataRequired()])
    fee_rate = FloatField('交易费率(%)', validators=[NumberRange(min=0, max=10.0, message='交易费率必须在0.00到10.00之间')], default=0.0, filters=[lambda x: x if x is not None else 0.0])
    account = SelectField('资金账户', validators=[DataRequired()], coerce=int)
    family_member = SelectField('家庭成员', choices=[('', '-- 选择家庭成员 --')], validate_choice=False)
    description = StringField('备注')
    submit = SubmitField('提交')

class EditInvestmentHoldingForm(FlaskForm):
    quantity = FloatField('持仓数量', validators=[DataRequired(), NumberRange(min=0.01)])
    cost_price = FloatField('成本价', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('保存修改')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('用户名已存在')
            return redirect(url_for('register'))
        if User.query.filter_by(email=form.email.data).first():
            flash('邮箱已被注册')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码不正确')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    form = FlaskForm()
    # 获取筛选参数
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    category_name = request.args.get('category', 'all')

    # 构建查询
    query = Transaction.query.filter_by(user_id=current_user.id)

    # 日期筛选
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Transaction.date >= start_date)
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
        query = query.filter(Transaction.date <= end_date)

    # 类别筛选
    if category_name != 'all':
        query = query.join(Category).filter(Category.name == category_name)

    transactions = query.order_by(Transaction.date.desc()).all()

    # 收支汇总
    income_total = sum(t.amount for t in transactions if t.category.type == 'income')
    expense_total = sum(t.amount for t in transactions if t.category.type == 'expense')
    balance = income_total - expense_total

    # 月支出和年支出统计
    current_date = datetime.now()
    current_month_start = datetime(current_date.year, current_date.month, 1)
    current_year_start = datetime(current_date.year, 1, 1)

    monthly_expense = sum(t.amount for t in transactions if t.category.type == 'expense' and t.date >= current_month_start)
    yearly_expense = sum(t.amount for t in transactions if t.category.type == 'expense' and t.date >= current_year_start)

    # 筛选表单
    filter_form = TransactionFilterForm()
    filter_form.category.choices = [('all', '所有类别')] + [(c.name, c.name) for c in Category.query.all()]
    if category_name != 'all':
        filter_form.category.data = category_name
    if start_date_str:
        filter_form.start_date.data = datetime.strptime(start_date_str, '%Y-%m-%d')
    if end_date_str:
        filter_form.end_date.data = datetime.strptime(end_date_str, '%Y-%m-%d')

    return render_template('dashboard.html', 
                          transactions=transactions, 
                          filter_form=filter_form, 
                          income_total=income_total, 
                          expense_total=expense_total, 
                          balance=balance, 
                          monthly_expense=monthly_expense, 
                          yearly_expense=yearly_expense, 
                          form=form)

@app.route('/add_account', methods=['GET', 'POST'])
@login_required
def add_account():
    form = AccountForm()
    if form.validate_on_submit():
        account = Account(
            name=form.name.data,
            type=form.type.data,
            balance=float(form.balance.data),
            user_id=current_user.id
        )
        db.session.add(account)
        db.session.commit()
        flash('账户添加成功')
        return redirect(url_for('dashboard'))
    return render_template('add_account.html', form=form)

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # 获取最新交易日期
    latest_transaction = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).first()
    default_date = latest_transaction.date.date() if latest_transaction else datetime.today().date()
    
    form = TransactionForm()
    # 获取类别选项
    categories = Category.query.all()
    form.category.choices = [(str(c.id), c.name) for c in categories]
    
    # 获取账户选项
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    form.account.choices = [(str(a.id), a.name) for a in accounts]
    
    # 获取家庭成员选项
    family_members = FamilyMember.query.filter_by(user_id=current_user.id).all()
    form.family_member.choices += [(str(m.id), m.name) for m in family_members]
    
    if request.method == 'GET':
        form.date.data = default_date
    
    if form.validate_on_submit():
        try:
            amount = float(form.amount.data)
            category_id = int(form.category.data)
            account_id = int(form.account.data)
            
            # 获取家庭成员ID（可为空）
            family_member_id = int(form.family_member.data) if form.family_member.data else None
            
            # 创建新交易
            new_transaction = Transaction(
                amount=amount,
                description=form.description.data,
                date=form.date.data,
                user_id=current_user.id,
                category_id=category_id,
                account_id=account_id,
                family_member_id=family_member_id
            )
            
            db.session.add(new_transaction)
            
            # 更新账户余额
            account = Account.query.get(account_id)
            if account:
                if Category.query.get(category_id).type == 'income':
                    account.balance += amount
                else:
                    account.balance -= amount
            
            db.session.commit()
            flash('交易添加成功', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加交易失败: {str(e)}', 'danger')
    
    return render_template('add_transaction.html', form=form)

@app.route('/edit_transaction/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        flash('无权操作此交易记录', 'danger')
        return redirect(url_for('dashboard'))
    
    form = TransactionForm(obj=transaction)
    # 获取类别选项
    categories = Category.query.all()
    form.category.choices = [(str(c.id), c.name) for c in categories]
    
    # 获取账户选项
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    form.account.choices = [(str(a.id), a.name) for a in accounts]
    
    # 获取家庭成员选项
    family_members = FamilyMember.query.filter_by(user_id=current_user.id).all()
    form.family_member.choices = [('','请选择家庭成员')] + [(str(m.id), m.name) for m in family_members]
    
    # 设置当前选中的家庭成员
    if transaction.family_member_id:
        form.family_member.data = str(transaction.family_member_id)
    
    if form.validate_on_submit():
        try:
            old_amount = transaction.amount
            old_category_id = transaction.category_id
            old_account_id = transaction.account_id
            
            # 更新交易信息
            transaction.amount = float(form.amount.data)
            transaction.description = form.description.data
            transaction.date = form.date.data
            transaction.category_id = int(form.category.data)
            transaction.account_id = int(form.account.data)
            transaction.family_member_id = int(form.family_member.data) if form.family_member.data else None
            
            # 更新账户余额
            old_account = Account.query.get(old_account_id)
            if old_account:
                # 回滚旧交易对账户余额的影响
                if Category.query.get(old_category_id).type == 'income':
                    old_account.balance -= old_amount
                else:
                    old_account.balance += old_amount
            
            new_account = Account.query.get(transaction.account_id)
            if new_account:
                # 应用新交易对账户余额的影响
                if Category.query.get(transaction.category_id).type == 'income':
                    new_account.balance += transaction.amount
                else:
                    new_account.balance -= transaction.amount
            
            db.session.commit()
            flash('交易记录更新成功', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新交易失败: {str(e)}', 'danger')
    
    return render_template('edit_transaction.html', form=form)

@app.route('/delete_transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        abort(403)
    try:
        db.session.delete(transaction)
        db.session.commit()
        flash('交易记录已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败：{str(e)}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/accounts')
@login_required
def accounts():
    form = FlaskForm()
    user_accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('accounts.html', accounts=user_accounts, form=form)

@app.route('/edit_account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    if account.user_id != current_user.id:
        abort(403)
    form = AccountForm()
    if form.validate_on_submit():
        account.name = form.name.data
        account.type = form.type.data
        account.balance = form.balance.data
        db.session.commit()
        flash('账户更新成功！', 'success')
        return redirect(url_for('accounts'))
    elif request.method == 'GET':
        form.name.data = account.name
        form.type.data = account.type
        form.balance.data = account.balance
    return render_template('edit_account.html', title='编辑账户', form=form)

@app.route('/delete_account/<int:account_id>', methods=['POST'])
@login_required
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    if account.user_id != current_user.id:
        abort(403)
    try:
        db.session.delete(account)
        db.session.commit()
        flash('账户已删除！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('删除失败：该账户存在关联交易记录', 'danger')
    return redirect(url_for('accounts'))

@app.route('/family_members')
@login_required
def family_members():
    members = FamilyMember.query.filter_by(user_id=current_user.id).all()
    form = FamilyMemberForm()
    return render_template('family_members.html', members=members, form=form)

@app.route('/investment_dashboard')
@login_required
def investment_dashboard():
    # 投资仪表盘逻辑
    holdings = InvestmentHolding.query.filter_by(user_id=current_user.id).all()
    total_investment = sum(holding.quantity * holding.current_price for holding in holdings)
    # 计算总盈亏
    total_profit = sum(holding.quantity * (holding.current_price - holding.cost_price) for holding in holdings)
    # 假设昨日总投资为当前总投资的99%，实际应用中应从数据库获取历史数据
    previous_total = total_investment * 0.99
    daily_change = ((total_investment - previous_total) / previous_total) * 100 if previous_total > 0 else 0
    return render_template('investment_dashboard.html', holdings=holdings, total_investment=total_investment, daily_change=daily_change, total_profit=total_profit)

@app.route('/edit_investment_holding/<int:holding_id>', methods=['GET', 'POST'])
@login_required
def edit_investment_holding(holding_id):
    holding = InvestmentHolding.query.get_or_404(holding_id)
    form = EditInvestmentHoldingForm(obj=holding)
    
    if form.validate_on_submit():
        holding.quantity = form.quantity.data
        holding.cost_price = form.cost_price.data
        db.session.commit()
        flash('持仓信息已成功更新', 'success')
        return redirect(url_for('investment_dashboard'))
    
    return render_template('edit_investment_holding.html', holding=holding, form=form)

def investment_dashboard():
    # 获取用户所有投资持仓
    holdings = InvestmentHolding.query.filter_by(user_id=current_user.id).all()
    
    # 计算投资总资产
    total_investment = sum(holding.quantity * holding.current_price for holding in holdings)
    
    # 计算持仓数量
    holding_count = len(holdings)
    
    # 计算累计收益和收益率
    total_cost = sum(holding.quantity * holding.cost_price for holding in holdings)
    total_profit = total_investment - total_cost
    profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    # 获取可用投资资金（所有账户余额总和）
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    available_funds = sum(account.balance for account in accounts)
    
    # 模拟日变化数据
    daily_change = 0.5  # 实际应用中应该根据历史数据计算
    
    # 准备图表数据
    portfolio_labels = []
    portfolio_data = []
    type_labels = []
    type_data = []
    type_summary = {}
    
    for holding in holdings:
        product_name = holding.product.name
        market_value = holding.quantity * holding.current_price
        
        # 持仓占比数据
        portfolio_labels.append(product_name)
        portfolio_data.append(market_value)
        
        # 投资类型分布数据
        product_type = holding.product.type
        if product_type not in type_summary:
            type_summary[product_type] = 0
        type_summary[product_type] += market_value
    
    # 格式化投资类型数据
    type_mapping = {
        'money_fund': '货币基金',
        'etf': 'ETF基金',
        'stock': '股票',
        'repo': '逆回购'
    }
    for type_code, value in type_summary.items():
        type_labels.append(type_mapping.get(type_code, type_code))
        type_data.append(value)
    
    return render_template('investment_dashboard.html',
                          holdings=holdings,
                          total_investment=total_investment,
                          holding_count=holding_count,
                          total_profit=total_profit,
                          profit_rate=profit_rate,
                          available_funds=available_funds,
                          daily_change=daily_change,
                          portfolio_labels=json.dumps(portfolio_labels),
                          portfolio_data=json.dumps(portfolio_data),
                          type_labels=json.dumps(type_labels),
                          type_data=json.dumps(type_data))

@app.route('/add_investment_product', methods=['GET', 'POST'])
@login_required
def add_investment_product():
    form = InvestmentProductForm()
    if form.validate_on_submit():
        # 检查产品代码是否已存在
        if InvestmentProduct.query.filter_by(code=form.code.data, user_id=current_user.id).first():
            flash('该产品代码已存在', 'danger')
            return redirect(url_for('add_investment_product'))
        
        product = InvestmentProduct(
            name=form.name.data,
            code=form.code.data,
            type=form.type.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('投资产品添加成功', 'success')
        return redirect(url_for('investment_dashboard'))
    return render_template('add_investment_product.html', form=form)

@app.route('/add_family_member', methods=['GET', 'POST'])
@login_required
def add_family_member():
    form = FamilyMemberForm()
    if form.validate_on_submit():
        member = FamilyMember(
            name=form.name.data,
            relationship=form.relationship.data,
            user_id=current_user.id
        )
        db.session.add(member)
        db.session.commit()
        flash('家庭成员添加成功', 'success')
        return redirect(url_for('family_members'))
    return render_template('add_family_member.html', form=form)

@app.route('/add_investment_transaction', methods=['GET', 'POST'])
@login_required
def add_investment_transaction():
    form = InvestmentTransactionForm()
    
    # 获取投资产品选项
    products = InvestmentProduct.query.filter_by(user_id=current_user.id).all()
    if products:
        form.product.choices = [(p.id, f'{p.name} ({p.code})') for p in products]
    else:
        form.product.choices = [(0, '请先添加投资产品')]
    
    # 获取账户选项
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    form.account.choices = [(a.id, a.name) for a in accounts]
    
    # 获取家庭成员选项
    family_members = FamilyMember.query.filter_by(user_id=current_user.id).all()
    form.family_member.choices += [(m.id, m.name) for m in family_members]
    
    if form.validate_on_submit():
        try:
            product_id = form.product.data
            transaction_type = form.transaction_type.data
            quantity = float(form.quantity.data)
            price = float(form.price.data)
            account_id = form.account.data
            family_member_id = form.family_member.data if form.family_member.data and form.family_member.data != '' else None
            description = form.description.data
            amount = quantity * price
            
            # 获取相关对象
            product = InvestmentProduct.query.get_or_404(product_id)
            account = Account.query.get_or_404(account_id)
            
            # 检查账户余额（买入/赎回时）
            if transaction_type in ['buy', 'redeem'] and account.balance < amount:
                flash('账户余额不足', 'danger')
                return redirect(url_for('add_investment_transaction'))
            
            # 创建交易记录
            transaction = InvestmentTransaction(
                product_id=product_id,
                transaction_type=transaction_type,
                quantity=quantity,
                price=price,
                amount=amount,
                user_id=current_user.id,
                family_member_id=family_member_id,
                account_id=account_id,
                description=description,
                fee_rate=form.fee_rate.data
            )
            db.session.add(transaction)
            
            # 更新账户余额
            if transaction_type in ['buy', 'redeem']:
                account.balance -= amount
            else:  # sell
                account.balance += amount
            
            # 更新持仓记录
            holding = InvestmentHolding.query.filter_by(
                product_id=product_id,
                user_id=current_user.id,
                account_id=account_id
            ).first()
            
            if transaction_type in ['buy', 'redeem']:  # 买入/申购
                if holding:
                    # 更新现有持仓（加权平均成本）
                    total_cost = holding.quantity * holding.cost_price + amount
                    total_quantity = holding.quantity + quantity
                    holding.cost_price = total_cost / total_quantity
                    holding.quantity = total_quantity
                else:
                    # 创建新持仓
                    holding = InvestmentHolding(
                        product_id=product_id,
                        quantity=quantity,
                        cost_price=price,
                        current_price=price,  # 初始当前价等于买入价
                        user_id=current_user.id,
                        family_member_id=family_member_id,
                        account_id=account_id
                    )
                    db.session.add(holding)
            else:  # 卖出/赎回
                if not holding or holding.quantity < quantity:
                    flash('持仓数量不足', 'danger')
                    db.session.rollback()
                    return redirect(url_for('add_investment_transaction'))
                
                holding.quantity -= quantity
                # 如果持仓数量为0，删除持仓记录
                if holding.quantity <= 0:
                    db.session.delete(holding)
            
            db.session.commit()
            flash('投资交易成功', 'success')
            return redirect(url_for('investment_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'交易失败: {str(e)}', 'danger')
    
    return render_template('add_investment_transaction.html', form=form)

@app.route('/edit_family_member/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_family_member(id):
    member = FamilyMember.query.get_or_404(id)
    if member.user_id != current_user.id:
        flash('无权操作此家庭成员', 'danger')
        return redirect(url_for('family_members'))
    
    form = FamilyMemberForm(obj=member)
    if form.validate_on_submit():
        member.name = form.name.data
        member.relationship = form.relationship.data
        db.session.commit()
        flash('家庭成员信息更新成功', 'success')
        return redirect(url_for('family_members'))
    return render_template('edit_family_member.html', form=form)

@app.route('/sell_investment/<int:product_id>', methods=['GET', 'POST'])
@login_required
def sell_investment(product_id):
    product = InvestmentProduct.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('无权操作此投资产品', 'danger')
        return redirect(url_for('investment_dashboard'))
    
    # 获取该产品的持仓记录
    holdings = InvestmentHolding.query.filter_by(
        product_id=product_id,
        user_id=current_user.id
    ).all()
    
    if not holdings:
        flash('没有该产品的持仓记录', 'danger')
        return redirect(url_for('investment_dashboard'))
    
    # 创建表单
    class SellInvestmentForm(FlaskForm):
        holding = SelectField('持仓账户', validators=[DataRequired()], coerce=int)
        quantity = StringField('卖出数量', validators=[DataRequired()])
        price = StringField('卖出价格', validators=[DataRequired()])
        description = StringField('备注')
        submit = SubmitField('确认卖出')
    
    form = SellInvestmentForm()
    
    # 设置持仓选项
    form.holding.choices = [(h.id, f'{h.account.name} (持有: {h.quantity})') for h in holdings]
    
    if form.validate_on_submit():
        try:
            holding_id = form.holding.data
            quantity = float(form.quantity.data)
            price = float(form.price.data)
            description = form.description.data
            amount = quantity * price
            
            # 获取持仓记录
            holding = InvestmentHolding.query.get_or_404(holding_id)
            if holding.quantity < quantity:
                flash('持仓数量不足', 'danger')
                return redirect(url_for('sell_investment', product_id=product_id))
            
            # 创建交易记录
            transaction = InvestmentTransaction(
                product_id=product_id,
                transaction_type='sell',
                quantity=quantity,
                price=price,
                amount=amount,
                user_id=current_user.id,
                family_member_id=holding.family_member_id,
                account_id=holding.account_id,
                description=description
            )
            db.session.add(transaction)
            
            # 更新账户余额
            account = Account.query.get_or_404(holding.account_id)
            account.balance += amount
            
            # 更新持仓记录
            holding.quantity -= quantity
            if holding.quantity <= 0:
                db.session.delete(holding)
            
            db.session.commit()
            flash('卖出成功', 'success')
            return redirect(url_for('investment_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'卖出失败: {str(e)}', 'danger')
    
    return render_template('sell_investment.html', form=form, product=product)

@app.route('/view_investment_details/<int:product_id>', methods=['GET'])
@login_required
def view_investment_details(product_id):
    product = InvestmentProduct.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('无权查看此投资产品', 'danger')
        return redirect(url_for('investment_dashboard'))
    
    # 获取持仓记录
    holdings = InvestmentHolding.query.filter_by(
        product_id=product_id,
        user_id=current_user.id
    ).all()
    
    # 获取交易历史
    transactions = InvestmentTransaction.query.filter_by(
        product_id=product_id,
        user_id=current_user.id
    ).order_by(InvestmentTransaction.transaction_date.desc()).all()
    
    # 计算总持仓数量和市值
    total_quantity = sum(h.quantity for h in holdings)
    total_market_value = sum(h.quantity * h.current_price for h in holdings)
    total_cost = sum(h.quantity * h.cost_price for h in holdings)
    total_profit = total_market_value - total_cost
    profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0
    
    return render_template('view_investment_details.html',
                          product=product,
                          holdings=holdings,
                          transactions=transactions,
                          total_quantity=total_quantity,
                          total_market_value=total_market_value,
                          total_cost=total_cost,
                          total_profit=total_profit,
                          profit_rate=profit_rate)

@app.route('/delete_family_member/<int:id>', methods=['POST'])
@login_required
def delete_family_member(id):
    member = FamilyMember.query.get_or_404(id)
    if member.user_id != current_user.id:
        flash('无权操作此家庭成员', 'danger')
        return redirect(url_for('family_members'))
    
    try:
        db.session.delete(member)
        db.session.commit()
        flash('家庭成员删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    return redirect(url_for('family_members'))

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--port', type=int, default=5000)
    # args = parser.parse_args()
    # app.run(debug=True, port=args.port)
    app.run(debug=True, port=5000)