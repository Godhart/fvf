# Подробное описание объектов фреймворка

## Описания сущностей

### Введение

Как было сказано, сущности могут быть следующего типа:

* Абстракции объектов из реального мира или другой программной системы, к которой можно обеспечить программный доступ
прямым или косвенным образом

* Объекты фреймворка - специальные сущности, обеспечивающие формализацию тестирования

* Прочие объекты описанные на языке Python, выполняемые движком фреймморка, обеспечивающие дополнительные, 
связующие абстрации

Примеры сущностей-абстракций:
* Хост - узел в вычислительной сети (и для примера имеющий трансивер радиоканала определённого типа)
* Приложениие - экземпляр приложения запущенный на хосте, с которым возможно взаимодействие через TCP сокет
* Лампочка с управлением по радиоканалу
* Реле с управлением по радиоканалу
* Лампочка, подключенная к реле с управлением по радиокналу
* Клапан, включение и выключением которым осуществляется механическим манипулятором, управялемым программно 
(к примеру - управяляемым программой, запущенной на хосте, с которой возможно взаимодействие посредством 
какого-либо интерфейса, к примеру TCP)
и т.п.

Примеры сущностей объектов, выполняемых движком, обеспечивающих дополнительные абстракции:
* Блок передачи данных через сокет TCP
* Блок выполнения запросов HTTP
* Блок выполнения запросов REST API

Сущности ообъектов фреймворка: --требуется их реализация--
* Scoreboard
* Coverage
* Sequencer
Эти сущности подробно рассмотрены в разделе ...

Можно использовать следующие примеры описания сущностей при чтении данного раздела:
-- привести список и ссылки - Host, Calc, SoftwareRunner, TcpIO --

### Основы описания сущностей

#### Основные принципы

В фреймворке помещаются описания типов сущностей

Все описания типов сущностей должны быть классами Python и должны быть унаследованы от класса `PlatformBase` 
из модуля `platformix` пакета `core` -- ссылка --, или от других классов, унаследованных от него.

Описание каждого типа сущности должно содержаться в модуле `main` в пакете с именем соответствующему типу и который (пакет)
должен быть расположен внутри пакета `platforms`. Класс с описанием типа сущности дожен иметь имя `RootClass`.

#### Исключения в именовании типов сущностей

В качестве типа сущности НЕ следует использовать следующие имена:
`name`, `fw`, `description`, `generics`, `generate`, `alias`, `model`, `include`, `subenv`, `group`, `platforms`, 
`extension`

#### Инициализация, запуск и остановка

При выполнении проверок экземпляры сущностей создаются на следующем шаге после загрузки описания тестового окружения.
Необходимые значения параметров для конструктора задаются в описании тестового окружения.
В конструкторе сущности должен находиться только код по иницализации --переменных-- экземпляра класса, а так же 
подключение поддержки реализаций требуемых интерфейсов (протоколов).
Установка связи сущности-абстракции с реальными объектами, приведение их в определённое состояние перед проведением 
проверки и т.п. осуществляется на последующих этапах.\
_*! Внимание!* Не забывайте про конструтор родительского класса! Он должен вызываться в первую очередь в констукторе 
сущности_

_*! Внимание!* Следующие имена зарезервированы и *НЕ МОГУТ* быть использованы в аргументах конструктора:_
* `condition`
* `subplatforms`

Действия, необходимые для работы экземпляра сущности при проведении проверки, такие как установка соединения, 
запуск внешнего приложения, копирование файлов, приведение связанных с сущностями реальных объектов
в необходимое состояние перед проведением проверки и т.п. должно осуществляться в методе `_start`.\
_*! Внимание!* В конце метода *\_start* должен вызываться метод `_start` родительского объекта (`super(...)._start(...`)_

Действия, необходимые после завершения проверки, такие как разрыв соединения, остановка внешнего 
приложения, удаление файлов при необходимости и т.п. должны осуществляться в методе `_stop`.\
_*! Внимание !* В конце метода *\_stop* должен вызываться метод `_stop` родительского объекта (`super(...)._stop(...`)_

Метод `_start` вызывается перед проведением проверки, метод `_stop` вызывается после проведения проверки.\
За время жизни экземпляра сущности методы `_start` и `_stop` могут вызываться много раз

#### Перечень обязательных методов и переменных

Помимо упомянутых методов `_start` и `_stop` каждый экземпляр сущности должен иметь перечисленные ниже методы и 
переменные.Все они входят в базовый класс `PlatformBase`.

##### Общие переменные и методы необходиые для поддержки протоколов

Перечисленные ниже методы и переменные должны присутствовать в объекте сущности для обеспечения работы протоколов

В случае перекрытия приведённых здесь методов, их интерфейс (--сигнатура--) и суть выполняемых ими операций, должны 
сохраняться.

Назначение переменных меняться не должно

Методы:
* `_reply`:     - отправка ответа
* `_reply_all`: - отправка ответа всем в списке
* `_register_reply_handler`:   - зарегистриовать call-back функцию реакции на ответ
* `_unregister_reply_handler`: - снять регистрацию call-back функции реакции на ответ

Переменные:
* `_running`:   - переменная типа *bool*. `True` обозначает, что экземпляр запущен (успешно выполнил метод *\_start*)
и готов выполнять запросы. `False` обозначает, что экземпляр ещё не запущен (не был запущен, ожидает завершения запуска, 
ожидает оставновки или остановлен) и соответственно не может выполнять запросы

##### --Переменные-- и методы для интегарции с фреймворком

-- `send`, `request` и т.п. -- 

`_farm`, `_wait`, `_start_max_wait`, `_stop_max_wait`

#### Поддержка базового протокола 'platformix'

Протокол `platformix` обеспечивает корректное взаимодействие фреймворка с сущностями (в частности запуск и их остановку)
, а так же базовые операции такие как прочитать/записать перменную объекта сущности или свойство (`@property`), вызвать
метод, --сделать слепок состояния--

Базовый клас `PlatformBase` изначально поддерживает этот протокол и производные от него классы не должны убирать эту 
поддержку.

Перечисленные разделом выше методы `_start` и `_stop` в т.ч. являются и реализацией методов базового протокола 
`platformix`

Помимо данных методов в сущности должны иметься следующие переменные протокола `platformix`:
`_starting`, `_start_in_progress`, `_stopping`, `_stop_in_progress`

Эти переменные уже есть в базовом классе `PlatformBase` и их использование не должно перекрываться производными классами

#### Описание специфичного для сущности функционала

Функционал, специфичный для конкретной сущности, может быть описан следующим образом:

1. Путём добавления свойств объекта (`@property`), при обращении к которым будут выполняться неоходимые действия. 

Значение свойства возвращается как результат. Такие обращения должны быть атомарными - не треобвать 
для корректной работы определённой последовательности обращений к другим свойствам сущности.
Для обращения к свойствам сущности используются методы `get` и `set` интерфейса `platformix`

2. Путём подключения поддержки определённых интерфейсов.

Поддержка какого любо интерфейса обеспечивается поддержкой одной из реализаций его протокола (далее просто протокола).
Для поддержки протокола, в сущности должны быть определены переменные и методы, перечисленные в спецификации протокола.

Методы обеспечивают специфичную для этой сущности реализацию методов протокола (но не самого протокола).

Переменные обеспечивают хранение контекста протокола.

Поддержка протокола должна быть объявлена в конструкторе сущности, для подробностей см. подключение поддержки 
протоколов.

В случае отсутствия подходящего протокола он д.б. предварительно разработан и описан, для подробностей см. раздел 
описания интерфейсов и протоколов

Пример сущности, содержащей только свойства: --host--
Пример сущности, имеющей поддержку протокола: --calc--

### Подключение поддержки интерфейса

Для продолжения сперва следует ознакомиться с разделом описания интерфейсов и протоколов

#### Общий принцип

Пакеты, вложенные в пакет `ip` фактичеси представляют собой перечень возможных для поддержки интерфейсов

Подключение поддержки интерфейса происходит неявно за счёт поддержки одной из реализаций его протокола.

Для поддержки требуемого протокола в первую очередь в модуле описания сущности необходимо импортировать класс описания 
требуемой реализации протокола, а так же класс создания объекта-обёртки для упрощения связи этого протокола с описанием 
сущности.

Для объявления поддержки объектом сущности необходимого протокола в конструкторе сущности вызывается метод 
`_support_protocol`, унаследованный им от класса `PlatformBase`, в который передаётся свежесозданный экземпляр объекта 
реализации протокола требуемого интерфейса.

Пример класса протокола: --arith_protocol-- (протокол выполнения арифметических операций, 
используется в примере использования фреймворка)

Пример класса для создания объекта-обёртки для протокола: --arith_protocol_wrapper--

#### Использование объекта-обёртки

Исходно при создании экземпляра объекта описнаия протокола в его конструктор требуется передать ссылку на объект, 
содержащий переменные и реализацию методов, с именами, указанными в переменных `_protocol_fields` и `_protocol_methods` 
класса описания неоходимого протокола

Для упомянутого в примере класса протокола --arith_protocol-- это ...

Поскольку одной из целью создания данного фреймворка было упрощение описания, то для исключения создания сложной 
иерархии классов изначально предусмотрено использование самого объекта сущности в качестве такого объекта. 
Однако подход "в лоб" вызовет понятные неудобства из-за необходимости наличия требуемых имён переменных и методов 
протокола в описании сущности, т.к. возможны пересечения имён а так же из-за --публичной доступности-- этих имеён
 
В связи с этим предлагается следующий механизм (который будет продемонстрирован в следующем разделе):

1. Имена переменных и методов сущности, которые будут использованы протоколом, объявляются с использованием какого-либо 
префикса, общего для всех, относящемуся к одному протоколу. Подразумевается, что в простейшем случае в качестве префикса
будет символ подчёркивания `_`

2. После этого, в конструкторе сущности создаётся объект-обёртки с правильными именами методов и переменных. 
Этот объект создаётся автоматоматическим образом с помощью класса создания объекта-обёртки. В качестве параметров 
методу этого класса указывается экземпляр сущности и использованный общий префикс.

3. Этот объект передаётся в конструктор протокола.

4. Обращения из протокола к методам и свойствам этого объекта будут переадресовываться к метоадам и переменным экземпляра 
сущности.

#### Варианты обеспечения поддержки протокола объектом сущности

Как указано выше для поддержки одной из реализаций протокола интерфейса необходимо в сущноости объявить требуемые для 
данной реализации протокола переменные а так же реализовать требуемые методы

Ниже приведены примеры вариантов реализации этого требования.

К примеру для поддержки упоминавшегося раннее протокола `arith` в объекте сущности необходимо иметь 
переменную `running` и методы `sum`, `sub`, `mult`, `div`, `power`, `reply`, `reply_all`, 
причём `running`, `reply`, `reply_all` являются общими для всех протоколов, как было указано в разделе --...--

##### Вариант I (по умполчанию)
Поскольку `running`, `reply_all` и `reply` есть в каждом классе описания сущности и имеют префикс `_`, то для простоты 
можно использовать этот же префикс для имён переменных и методов протокола 

1. В класс добавляются недостающие методы `_sum`, `_sub`, `_mult`, `_div`, `_power`

2. В конструкторе объекта добавляется следующий код:

```python
# Создание объекта-обёртки. ArithWrapper - класс из модуля определения интерфейса Arith (src/ip/arith/definitions.py)
self.arith = ArithWrapper.get_wrapper(self, None, None, "_")

# В этом и последующих примерах ссылка на объект-обёртку добавлена в публичные переменные объекта, но это не обязательно`

# Добавление протокола в перечень поддерживаемых объектом
self._support_protocol(ArithProtocol(self, self.arith))
```

##### Вариант II (создание свойств-алиасов и методов-алиасов)
В более сложном случае, если бы один из методов `_sum`, `_sub`, `_mult`, `_div`, `_power` пересекался с другими методами
 сущности, в т.ч. для поддержки какого-то другого протокола возможно было бы решить задачу следующими способом:

1. Использовать другой префикс для методов `sum`, `sub` и т.д. (в данном примере используется префикс `_arith_`)
Т.е. в класс будут добавлены методы `_arith_sum`, `_arith_sub`, `_arith_mult`, `_arith_div`, `_arith_power`

2. Созздать алиасы для переменной `_running`, и методов `_reply` и `_reply_all` с нужным префиксом следующим образом:
--TODO: импорт модуля хелперов для функций alias--
```python
self._arith_running = alias_property(self._running) # -- TODO: --
self._arith_reply = alias_method(self._reply)       # -- TODO: --
self._arith_running = alias_method(self._reply_all) # -- TODO: --
```

3. Добавить код в конструктор с указанием использованного префикса (отличается от варианта 1 только префиксом):

```python
self.arith = ArithWrapper.get_wrapper(self, None, None, "_arith_")
self._support_protocol(ArithProtocol(self, self.arith))
```

Данный вариант хорош тем, что префиксом явно выделяются переменные и методы, относящиеся к поддержке определённого
протокола, однако требуется немного больше кода

##### Вариант III (явное указание соответствия имён)
Адьтернативное решение проблемы, описанной в варианте II - т.е. случая, если бы одно из имён методов `_sum`, `_sub`, 
`_mult`, `_div`, `_power` пересекалось с другими методами сущности:

1. Для того метода, имя которого пересекается с сущесвующим использовать другой префикс. 
Для примера пусть это будет метод `sum` и пусть он будет реализован методом `_arith_sum`, 
остальные - реализуются методами с префиксом по умолчанию, т.е. в сущности ещё 
будут методы `_sub`, `_mult`, `_div`, `_power`

2. При создании объекта обёртки указывать соответствие имени метода, префикс которого отличается от общего:

```python
self.arith = ArithWrapper.get_wrapper(self, None, {'sum':'_arith_sum'}, "_")
self._support_protocol(ArithProtocol(self, self.arith))
```

Аналогичным способом возможно задавть соотетствие имён переменных, т.е. в варианте II можно было бы обойтись без 
дополнительных алиасов следующим обраом:

```python
self.arith = ArithWrapper.get_wrapper(
    self,
    {'running':'_running'},                        # Соответствие имён переменных
    {'reply':'_reply', 'reply_all':'_reply_all'},  # Соответствие имён методов
    "_arith_sum")                                  # Префикс для всех не упомянутых
# -- TODO: '_running' or self._running?--

self._support_protocol(ArithProtocol(self, self.arith))
```