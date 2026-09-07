import sqlite3
from datetime import datetime
import os

class Database:
    def __init__(self):
        # Use a persistent database file in the app directory
        db_path = os.path.join(os.path.dirname(__file__), 'users.db')
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                staked_amount REAL DEFAULT 0,
                staked_time TEXT,
                last_reward_claim TEXT,
                total_earned REAL DEFAULT 0,
                referral_code TEXT,
                referred_by INTEGER
            )
        ''')
        
        # Transactions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                timestamp TEXT,
                description TEXT
            )
        ''')
        
        self.conn.commit()
    
    def register_user(self, user_id, username, first_name):
        try:
            self.cursor.execute(
                'SELECT user_id FROM users WHERE user_id = ?',
                (user_id,)
            )
            if not self.cursor.fetchone():
                self.cursor.execute(
                    'INSERT INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 100)',
                    (user_id, username, first_name)
                )
                self.conn.commit()
                # Add initial welcome bonus
                self.add_transaction(user_id, 'BONUS', 100, 'Welcome bonus 100 tokens')
                return True
            return False
        except Exception as e:
            print(f"Error registering user: {e}")
            return False
    
    def get_user(self, user_id):
        try:
            self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_balance(self, user_id, amount):
        try:
            self.cursor.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating balance: {e}")
            return False
    
    def stake_tokens(self, user_id, amount):
        try:
            user = self.get_user(user_id)
            if user and user[3] >= amount:
                self.cursor.execute(
                    'UPDATE users SET balance = balance - ?, staked_amount = staked_amount + ?, staked_time = ? WHERE user_id = ?',
                    (amount, amount, datetime.now().isoformat(), user_id)
                )
                self.conn.commit()
                self.add_transaction(user_id, 'STAKE', amount, f'Staked {amount} tokens')
                return True
            return False
        except Exception as e:
            print(f"Error staking tokens: {e}")
            return False
    
    def unstake_tokens(self, user_id):
        try:
            user = self.get_user(user_id)
            if user and user[4] > 0:
                amount = user[4]
                self.cursor.execute(
                    'UPDATE users SET balance = balance + ?, staked_amount = 0, staked_time = NULL WHERE user_id = ?',
                    (amount, user_id)
                )
                self.conn.commit()
                self.add_transaction(user_id, 'UNSTAKE', amount, f'Unstaked {amount} tokens')
                return True
            return False
        except Exception as e:
            print(f"Error unstaking tokens: {e}")
            return False
    
    def claim_rewards(self, user_id):
        try:
            user = self.get_user(user_id)
            if user and user[4] > 0 and user[5]:
                staked_time = datetime.fromisoformat(user[5])
                time_diff = datetime.now() - staked_time
                hours = time_diff.total_seconds() / 3600
                
                # 5% reward per hour
                reward = user[4] * 0.05 * hours
                
                if reward > 0:
                    self.cursor.execute(
                        'UPDATE users SET balance = balance + ?, total_earned = total_earned + ?, last_reward_claim = ? WHERE user_id = ?',
                        (reward, reward, datetime.now().isoformat(), user_id)
                    )
                    self.conn.commit()
                    self.add_transaction(user_id, 'REWARD', reward, f'Claimed {reward:.2f} tokens reward')
                    return reward
            return 0
        except Exception as e:
            print(f"Error claiming rewards: {e}")
            return 0
    
    def add_transaction(self, user_id, type, amount, description):
        try:
            self.cursor.execute(
                'INSERT INTO transactions (user_id, type, amount, timestamp, description) VALUES (?, ?, ?, ?, ?)',
                (user_id, type, amount, datetime.now().isoformat(), description)
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error adding transaction: {e}")
    
    def get_transactions(self, user_id, limit=10):
        try:
            self.cursor.execute(
                'SELECT type, amount, timestamp, description FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
                (user_id, limit)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    def get_top_stakers(self, limit=5):
        try:
            self.cursor.execute(
                'SELECT user_id, staked_amount FROM users WHERE staked_amount > 0 ORDER BY staked_amount DESC LIMIT ?',
                (limit,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting top stakers: {e}")
            return []
    
    def get_stats(self):
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            total_users = self.cursor.fetchone()[0]
            
            self.cursor.execute('SELECT SUM(staked_amount) FROM users')
            total_staked = self.cursor.fetchone()[0] or 0
            
            self.cursor.execute('SELECT SUM(total_earned) FROM users')
            total_rewards = self.cursor.fetchone()[0] or 0
            
            return total_users, total_staked, total_rewards
        except Exception as e:
            print(f"Error getting stats: {e}")
            return 0, 0, 0
