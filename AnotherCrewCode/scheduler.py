"""
Модуль планировщика задач.

Управляет регулярными напоминаниями и мотивационными сообщениями.
"""
import logging
import random
import datetime
from typing import Callable, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config

# Настройка логирования
logger = logging.getLogger(__name__)

class TaskScheduler:
    """Планировщик задач для регулярных уведомлений."""
    
    def __init__(self):
        """Инициализация планировщика."""
        self.scheduler = BackgroundScheduler()
        self.user_callbacks = {}  # Словарь с колбэками для всех типов уведомлений
        logger.info("Инициализирован планировщик задач")
    
    def start(self):
        """Запускает планировщик."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Планировщик запущен")
    
    def shutdown(self):
        """Останавливает планировщик."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик остановлен")
    
    def register_user(self, user_id: str, callback_functions: Dict[str, Callable]):
        """
        Регистрирует пользователя в планировщике.
        
        Args:
            user_id: ID пользователя
            callback_functions: Словарь с функциями обратного вызова для разных типов уведомлений
                (morning, evening, motivation)
        """
        self.user_callbacks[user_id] = callback_functions
        logger.info(f"Пользователь {user_id} зарегистрирован в планировщике")
    
    def unregister_user(self, user_id: str):
        """
        Удаляет пользователя из планировщика.
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self.user_callbacks:
            del self.user_callbacks[user_id]
            logger.info(f"Пользователь {user_id} удален из планировщика")
    
    def _schedule_morning_reminder(self):
        """Планирует утренние напоминания для всех пользователей."""
        # Разбираем время
        hour, minute = map(int, config.MORNING_TIME.split(':'))
        
        # Регистрируем задачу
        self.scheduler.add_job(
            self._send_morning_reminders,
            CronTrigger(hour=hour, minute=minute),
            id='morning_reminders',
            replace_existing=True
        )
        
        logger.info(f"Утренние напоминания запланированы на {config.MORNING_TIME}")
    
    def _schedule_evening_reminder(self):
        """Планирует вечерние опросы для всех пользователей."""
        # Разбираем время
        hour, minute = map(int, config.EVENING_TIME.split(':'))
        
        # Регистрируем задачу
        self.scheduler.add_job(
            self._send_evening_reminders,
            CronTrigger(hour=hour, minute=minute),
            id='evening_reminders',
            replace_existing=True
        )
        
        logger.info(f"Вечерние опросы запланированы на {config.EVENING_TIME}")
    
    def _schedule_motivation_messages(self):
        """Планирует отправку случайных мотивационных сообщений."""
        # Интервал между сообщениями (случайный в заданных пределах)
        hours = random.randint(
            config.MIN_MOTIVATIONAL_INTERVAL,
            config.MAX_MOTIVATIONAL_INTERVAL
        )
        
        # Регистрируем задачу
        self.scheduler.add_job(
            self._send_motivation_messages,
            IntervalTrigger(hours=hours),
            id='motivation_messages',
            replace_existing=True,
            next_run_time=datetime.datetime.now() + datetime.timedelta(hours=hours)
        )
        
        logger.info(f"Мотивационные сообщения запланированы каждые {hours} часов")
    
    def _send_morning_reminders(self):
        """Отправляет утренние напоминания всем пользователям."""
        logger.info("Отправка утренних напоминаний")
        
        for user_id, callbacks in self.user_callbacks.items():
            if 'morning' in callbacks:
                try:
                    callbacks['morning'](user_id)
                    logger.debug(f"Отправлено утреннее напоминание пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке утреннего напоминания пользователю {user_id}: {str(e)}")
    
    def _send_evening_reminders(self):
        """Отправляет вечерние опросы всем пользователям."""
        logger.info("Отправка вечерних опросов")
        
        for user_id, callbacks in self.user_callbacks.items():
            if 'evening' in callbacks:
                try:
                    callbacks['evening'](user_id)
                    logger.debug(f"Отправлен вечерний опрос пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке вечернего опроса пользователю {user_id}: {str(e)}")
    
    def _send_motivation_messages(self):
        """Отправляет мотивационные сообщения всем пользователям и планирует следующую отправку."""
        logger.info("Отправка мотивационных сообщений")
        
        for user_id, callbacks in self.user_callbacks.items():
            if 'motivation' in callbacks:
                try:
                    callbacks['motivation'](user_id)
                    logger.debug(f"Отправлено мотивационное сообщение пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке мотивационного сообщения пользователю {user_id}: {str(e)}")
        
        # Планируем следующую отправку
        self._schedule_motivation_messages()
    
    def schedule_all_tasks(self):
        """Планирует все типы напоминаний."""
        self._schedule_morning_reminder()
        self._schedule_evening_reminder()
        self._schedule_motivation_messages()
        logger.info("Все задачи запланированы")

# Тестовая функция для демонстрации
def demo_callback(user_id, message_type):
    """Демонстрационная функция обратного вызова."""
    print(f"[{message_type.upper()}] Сообщение для пользователя {user_id}")

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Для демонстрации
    scheduler = TaskScheduler()
    
    # Регистрируем тестового пользователя
    test_user_id = "test_user"
    callbacks = {
        'morning': lambda user_id: demo_callback(user_id, 'morning'),
        'evening': lambda user_id: demo_callback(user_id, 'evening'),
        'motivation': lambda user_id: demo_callback(user_id, 'motivation')
    }
    
    scheduler.register_user(test_user_id, callbacks)
    
    # Планируем задачи с ближайшим выполнением для демонстрации
    scheduler.scheduler.add_job(
        scheduler._send_morning_reminders,
        'date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=5),
        id='demo_morning'
    )
    
    scheduler.scheduler.add_job(
        scheduler._send_evening_reminders,
        'date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=10),
        id='demo_evening'
    )
    
    scheduler.scheduler.add_job(
        scheduler._send_motivation_messages,
        'date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=15),
        id='demo_motivation'
    )
    
    print("Запуск демонстрации планировщика...")
    print("Сообщения будут появляться через 5, 10 и 15 секунд")
    
    # Запускаем планировщик
    scheduler.start()
    
    try:
        # Ждем завершения демонстрации
        import time
        time.sleep(20)
    except KeyboardInterrupt:
        pass
    finally:
        # Останавливаем планировщик
        scheduler.shutdown()
        
    print("Демонстрация завершена!") 