class ReqpipeError(Exception):
    """Базовая ошибка пакета."""


class RegistryError(ReqpipeError):
    """Нарушены правила реестра: контракт ссылается на несуществующий элемент, цикл и т. п."""


class ContractViolation(ReqpipeError):
    """Результат элемента не соответствует его выходному контракту."""

    def __init__(self, element_id: str, errors: list[str]):
        self.element_id = element_id
        self.errors = errors
        super().__init__(f"{element_id}: результат не соответствует контракту:\n" + "\n".join(errors))


class StateError(ReqpipeError):
    """Действие невозможно в текущем состоянии конвейера."""


class ExecutorError(ReqpipeError):
    """Исполнитель (агент) не смог выполнить задачу."""
