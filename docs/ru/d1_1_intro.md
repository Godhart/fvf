# Введение в FVF

## Назначение

Formal Verification Framework был разработан для:

* автоматизации управления проверкой объектов а так же систем, требующих для проверки гетерогенного тестового окружения,
содержащего в т.ч. не только программные объекты, но и объекты реального мира

* обеспечения проверки как при помощи тестов на базе заранее описанных последовательностей воздействий, так и 
при помощи автоматически формируемых воздействий и контроля результата на базе формального описания (формальной верификации)

* повтороного использования тестов при проверке на разных этапах - от модели до реальной физической реализации

FVF вдохновлён технологией верификации UVM, применяемой при разработке аппаратной части на языках System Verilog/VHDL 
и является попыткой частично перенести эту технологию для тестирования реальных реализаций аппаратуры а так же 
более крупных систем.

FVF использует декларативное описание тестового окружения на языке YAML, а так же описание объектов тестового 
окружения на языке Python.

## Что вы получите

Когда данный фреймворк заработает во всю силу

* Если вы уже используете формальную верификацию (по методолгоии UVM) при разработке аппаратной части вы сможете:
  * проводить верификацию физических реализаций на базе существующих формальных описаний;
  * начать описывать сложные воздействия используя Python и множество существующих для него пакетов.
  
* Если вы в рядах экспериментаторов и используете другой язык для описания устройств (MyHDL) или пользуетесь 
специальными инструментами, для разработки устройстве без написания RTL кода, то вы теперь сможете проводить формальную 
верификацию схожим образом как и в mainstream.

* Если вы занимаетесь разработкой ПО:
  * если вы боитесь формальных методов и пока не использовалии их потому что это сложно - это ваш шанс попробовать их -
  вы сможете постепенно вводить проверки по формальному описанию без необходимости сделать всё сразу и 
  если вы уже использовали Python для написания тестов, то вы сможете их адаптировать;
  * если для проведения теста у вас используется сложное тестовое окружение - вы можете возложить задачи по запуску
  и дирижированием объектами тестового окружения на плечи фреймворка.

* Если вы занимаетесь разработкой на стыке программной и аппаратной части, либо же проводите верификацию на уровне 
большой системы:
  * Вы сможете проводить смешанную верификацию программмной и аппаратной части.
  * Вы сможете проводить верификацию до того, как те или иные части будут реализованы. Для создания функциональных
  mock объектов вы сможете использовать в т.ч. формальное описание, экономя своё время засчёт раннего тестирования
  и за счёт повторного использования формального описания.
  
* Если вы занимаетесь улучшением методов верификации вы можете использовать ядро фреймворка для взаимодействия 
с объектами тестового окружения и сконцентрироваться на разработке самих методов.

## Что вы можете получить уже сегодня

На данный момент проект находится на стадии прототипа.

Сегодня вы уже сможете описывать тестовое окружение и объекты тестового окружения в большей степени так, как 
это задумано и проводить тесты на базе заранее описанных последовательностей воздействий и ожидаемых результатов.

Внедрение функциональной верификации является следующим этапом разработки фреймворка.

Интеграция фреймворка с другими инструментами, а так же функционал по распределенному выполнению тестов будет 
осуществляться постепенно по мере его развития и исходя из востребованности и сложности задачи.

## Входные данные

В набор входных данных, определяющих проводимую проверку, входят:

* Описание тестового окружения в виде описания иерархии объектов тестового окружения и их параметров

-- Collapse --

В объекты тестового окружения входят как объекты абстракции проверяемых сущностей, так и другие объекты обеспечивающие их
проверку.

Описание должно быть написанно в декларативном стиле на языке YAML. Описание тестового окружения может содержать 
параметры, значения которых можно задавать из коммандной строки, а так же выражения на языке Python для рассчёта 
производных значений


* Набор описаний объектов тестового окружения, написанных на языке Python, которые могут быть следующих типов:

  * Объекты абстракции проверяемых сущностей и других сущностей, непосредственно уавствующих в проверке, к которым можно
  обеспечить программный доступ прямым или косвенным образом

  * Объекты формиальной верификации

-- Collapse --

    * `Rules` - объекты, осуществляющие перевод формальной спецификации указанной в определённом формате 
    в формат, доступный другим объектам формальной верфифкации

    * `Coverage` - объекты фреймворка, обеспечивающие контроль полноты функционального покрытия тестами 
    (множества аргументов, состояний и переходов) -- Возможно нужно убрать это уточнение, т.к. оно ограничено --
    
    * `Sequencer` - объекты, обеспечивающие требуемую последовательность воздействий для полноты функционального покрытия,
    либо последовательность воздействий, сформированную по определённым законам

    * `ScoreBoard` - объекты, осуществляеющие контроль соответствия реального поведения сущностей, тому, 
    которое предполагает формальная спецификация
    
  > При проведении формальной верификации объекты `Sequencer`, `Coverage`, `Scoreboard` могут работать совместно для 
  формирования таких последовательностей воздействий, которые обеспечат полноту функционального покрытия в соответствии 
  с формальной спецификацией, а так же избегать формирования воздействий которые приводят к ошибкам.

  * Прочие объекты, описанные на языке Python, обеспечивающие дополнительные и связующие абстракции


* Перечень и алгоритмы проводимых проверок, описанных на языке Python. В описании алгоритма проверки содержится описание
цепочек воздействий на объекты тестового окружения для выполнения той или иной проверки и ожидаемое значение результата.\
Стоит отметить, что при использовании тоько формальной верификации данные тесты ограничиваются запуском лишь одной 
функции.

* При проведении формальной верификации так же требуются формальные спецификации проверяемых сущностей или системы 
из нескольких сущностей, созданной для проверки одной из них.

_Примечание: На данном этапе рзвития не поддерживается ни один принятый формат описания формальной спецификации, но 
изначально допускается, что может быть использовано несколько разных фоматов. Возможные форматы будут определены в 
последующих версиях._

## Принципы

FVF предполагает следующие принципы:

* Декларативне описание тестового окружения с возможностью его параметризации

* Строгое разделение описания объектов тестового окружения, на следующие части:

  * Интерфейсы, включающие в себя перечень методов для реализации определённого функционала

  * Протоколы, содержащие реализацию *правил* выполнения методов соответствующих интерфейсов (но не реализацию их специфики)\
  _Здесь и далее под протоколом подразумевается одна из реализаций протокола интерфейса, если иное не оговорено_

  * Описание присущей объекту специфики, включая реализации специфичных частей протоколов

* Каждый объект тестового окружения может обеспечивать реализацию нескольких интерфейсов

* Повторное использование описаний

  * Один интерфейс может иметь нексколько реализаций протокола
  
  * Каждая реализация протокола может быть поддержана объектами тестового окружения разного типа

  * Одно описание тестового окружения может быть использовано как фрагмент другого тестового окружения

  * Одно описание тестового окружения может быть использовано в сочетании с несколькими наборами тестов

  * Однин набор тестов может быть использован в сочетании с несколькими тестовыми оружениями

  * Одна формальная спецификация может быть применена к схожим сущностям разного типа
  
  * Одна формальная спецификация может быть использована при проверках в разных тестовых окружениях и в разных тестах
  
  * Описание одного класса объектов тестового окружения может наследовать описание другого класса

* Обеспечение проверок нескольких типов

  * Контроль соответствия резултьтата предопределённому, заранее описанному значению на чётко определённое, 
заранее описанное воздействие

  * Автоматический контроль соответствия результатов воздействиям в соответствии с формальной спецификацией

  * Допускаются разнообразые способы описания формальной спецификации

  * Возможность одновременного контроля соответсви нескольких сущностей формальной спецификации
  (по своей спецификации для каждой из сущностей)

  * Двойной контроль - дополнительный контроль результата по формальной спцификации при проверках на предопределённых
  воздействиях


## Устройство фреймворка

Фреймворк состоит из:

* Ядра, включающего в себя:

  * Систему создания, запуска и остановки объектов тестового окружения, в соответствии с описанием тестового 
  окружении

  * Систему выполнения тестов

  * Систему передачи сообщений как для взаимодействия с объектами тестового окружения из метода выполняемого теста,
  так и для взаимодействия объектов между собой
  
-- Collapse --
  
  Обеспечивается взаимодействие на уровне вызова методов интерфейсов, обращения к свойствам объектов, а так же передачи 
  обратно результатов вызовов и обращений. Взаимодействие оеспечивается на уровне 'один к одному' и 'один ко многим'.
  Взаимодействие м.б. обеспечено между объектами тестового окружения находящихся на любом уровне иерархии.

* Пополняеого пользователем набора описаний классов объектов тестового окружения, интерфейсов и протоколов в виде 
  классов Python.

  Расширение набора классов объектов, интерфейсов и протоколов на данном этапе развития обеспечивается путём расширения 
  базовых классов фреймворка производными классами и включением их в пакеты фреймворка.
  
## Интеграция с другими инструментами тестирования

Данный фреймворк опирается на объекты тестового окружения, описываемые на языке Python. И хотя этот язык позволяет
с достаточной лёгкостью описывать сложные вещи, используя в т.ч. множество доступных пактов Python, всё же определённые
вещи заметно проще делать с помощью других инструментов, например такие как взаимодействие с GUI, определённые API, 
аппаратные интерфейсы и т.п.

Кроме этого уже могут быть разработаны определённые вещи, которые захочется совместить в тестировании сс данным 
фреймворком.

Для этой цели предлагается разрабатывать специальные объекты тестового окружения, позволяющие обеспечить взаимодействие 
с другими инструментами посредством вызова приложений с определёнными параметрами, взаимодействия через API, сокеты, 
потоки ввода/вывода и другими сопсобами, которые могут обеспечить Python и требуемые инструменты.
