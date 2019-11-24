# Подробное описание объектов фреймворка

## Описание тестового окружения

Тестовое окружение представляет собой описание иерархии сущностей тестового окружения. Используемый язык описания - YAML

Один файл может содержать описания нескольких тестовых окружений, каждое из которых может быть выбрано для использования
при проверке посредством параметра при запуске.

Ввиду того, что, как будет показано ниже, описываемое тестовое окружение может быть параметризовано, а так же 
составляться по описаниям из нескольких файлов, информация о действующем при проверке описании может быть выведена
в текстовом виде, а так же в виде UML диаграммы (в формате описания PlantUML).

### Базовая структура описания:

```yaml
test_env:   # Начало описания тестового окружения или окружений.
            # Содержимое - структра (она же словарь или хеш), если окружение одно, или список структур, если описываемых
            # окружений несколько
```

В структуре содержатся поля, в которых находятся описания тестового окружения и входящих в него сущностей

Следующие имена полей зарезервированы для описания тестового окружения и не рекомендуется их использовать для 
обозначения типа сущности в целях упрощения описания:
`name`, `fw`, `description`, `generics`, `generate`, `alias`, `model`, `include`,`subenv`, `group`, `platforms`, `extension`

#### Обязательная поля описания тестового окружения
```yaml
  fw: "1.0.0" # Требуемая версия фреймворка
  name: <test_env_name>  # Строка с наименованием тестового окружения, отображающего его суть, или кратким описанием.
```

#### Опциональные поля описания тестового окружения
```yaml
  description: "<test_env long description goes here>" # Подробное описание тестового окружения
```

#### Поля расширенного описания тестового окружения

Поля `generics`, `generate`, `alias`, `model`, `include`, `subenv`, `group`, `platforms`, `extension` используются для
 расширенного описания тестового окружения и описаны немного далее в разделе --Расширенное описание тестового окружения--,
 т.к. требуют базового представления об описании сущностей для их собственного понимания

Остальные поля в описании тестового окружения считаются описаниями сущностей. Принцип описания сущностей в следующем разделе.

#### Описание иерархии сущностей тестового окражуения

Описание иерархии сущностей начинается на том же уровне, что и обязательные и расширенные поля описнаия тестового окружения 

Имя поля, описывающего сущности должно совпадать с их типом.

##### Формат описания иерархии сущностей тестового окражуения

```yaml
  <entity_type_A>:  # Имя поля, указанное как <entity_type_A>, соответствует типу описываемой сущности
    # Содержимым должена быть структура --словарь-- с описанием параетров (generics) сущности, или список таких структур,
    # если требуется описать несколько сущностей одного типа
    
    # При "плоском" стиле описания перечисляются все сущности указанного типа
    # При иерархическом - только сущности этого типа, находящиеся в верху иерархии
    - name: "<entity_1_name>"       # Строка с именем данной сущности чтобы отличать её от других. Наличие - ОБЯЗАТЕЛЬНО
                                    # Имя ДОЛЖНО быть уникальным в рамках всего тестового окружения    
      
      platform: "<entity_2_name>"   # Строка с именем сущности, которая будет являться "родителем" для данной сущности
                                    # Параметр опциональный, и не указывается при иерархическом стиле описания
                                    # При описании необходимо отслежиать циклические зависимости
                                    # В случае наличия циклической зависимости система остановит проверку на этапе 
                                    # загрузки тестового коружения
                                    # Если параметр не указан, и сущность не входит в по иерархии в другую, она на имеет родителя
                                    # Родитель нужен:
                                    # * для того, выполнять функции, требуемые этой сущности для реализации собственных
                                    #   - по умолчанию все запросы, если явно не указано, отправляются "родителю"
                                    # * для того, чтобы явным образом указать зависимость этой сущности от другой
                                    #   - запускается сперва родительская сущность, останавливаются сущности в обратном порядке
                                    
      wait:                         # Дополнительный список имён сущностей, трубемых для работы описываемой.
        - "<entity_3_name>"         # Запуск описываемой сущности будет отложен до завершения перечисленных здесь сущщностей
        - "<entity_4_name>"         # Отсановка сущностей осушествялеся в обратном порядке
                                    # В этом списке не должно быть сущностей, запуск которых зависит от описываемой
                                    # В случае наличия циклической зависимости система остановит проверку на этапе 
                                    # загрузки тестового коружения
                                    # Параметр опциональный
                                    
      channels:                     # Список каналов сообщений, на которые должна быть подписана сущсность
        - "<channel_1_name>"        # -- TODO: --
        - "<channel_2_name>"
        
      condition: <condition>        # Условие использования сущности:
                                    # * 0 для исколючения сущности из тестового окружения
                                    # * 1 для включения сущности в тестовое окружение
                                    # Параметр опциональный, по умолчанию True
                                    # Использование данного параметра обычно имеет смысл совместно с парамметрами 
                                    # тестового окружения (секция generics описания тестового окружения)
                                    # Пример такого использования приведён в разделе 'Экстраполяция значений в описании
                                    # тестового окружения'
                                    
      # Перечень параметров для конструктора экземпляра сущсноти
      # Имя поля - имя аргумента в конструкторе, значение - соответственно значение которое он получит
      # Тип значения должен соотвествовать ожидаемому типу аргумента. 
      # Возможные типы аргументов: string, int, float, list, dict. 
      # Для аругментов типа bool указывать целое число 0 для False или 1 для True
      # Так же можно указывать аргументы других типов за счёт экстраполяции строкового выражения "$e{<Python expression>}"
      # Подробнее об экстраполяции аргументов см.раздел 'Экстраполяция значений в описании тестового окружения'
      <contructor_argument_1_name>: <contructor_argument_1_value>
      <contructor_argument_2_name>: <contructor_argument_2_value>
      # Значения аргуменов list и dict описываются по правилам YAML
      <contructor_argument_3_name>:   # list
        - <value_1>
        - <value_2>
      <contructor_argument_4_name>:   # dict
        <key_1>: <value_1>
        <key_2>: <value_2>
      ...
      
      # Следующее поле используется при иерархическом стиле опиания
      subplatforms:                 # В содержимом описываеются сущсноти, для которых эта будет родителем
                                    # Формат описания сущностей полностью аналогичен их описанию в тестовом окружении
        <entity_type>: ...          
          - name: ...
          
    - name: "<entity_2_name>"       # Описние ещё одной сущности такого же типа при плоском стиле описания или если 
                                    # эта сущность в верху иерархии
      ...

  # Описане сущностей другого типа по тем же принципам
  <entity_type_B>:
     ...
```

Пример описания сущностей в тестовом окружении см. в --...--

##### Зарезервированные имена сущностей

Следующие имена сущснотей НЕ ДОЛЖНЫ быть использованы в описании тестового окружения:
`all`, `any`, `others`, `none`

##### Плоский и иерархический стиль описания

Возможно использование двух стилей описания иерархии - "плоского" и иерархического.

Плоский стиль подходит когда описание небольшое или не хочется усложнять восприятие большими отступами в тексте, 
а так же в случаях, когда требуется через параметр указывать сущность-родителя (для подробностей  см. раздел 
'Экстарполяция значений в описании тестового окружения').

В любом случае можно сочетать оба метода - для тесносвязанных структур использовать иерархический стиль, а "верхушки"
 этих структур описывать в "плоском" стиле

### Расширенное описание тестового окружения

#### Секция generics

Эта секция позволяет параметризовать само тестовое окружение и в последствии при запуске теста указывать его параметры
 из командной строки
 
##### Формат описания
```yaml
      generics: # Содержит структуру с перечнем параметров и их значениями по умолчанию
        # Имя поля - имя параметра, значение поля - значение параметра по умолчанию
        # Допустимые типы параметров: string, int, float, list, dict
        <generic_1_name>: <generic_1_default_value>
        <generic_2_name>: <generic_2_default_value>
        ...
        # Типы list и dict при подстановке преобразуются в строковое представление
        # Для перевода их к нужному типу используйте $l{${generic_name}} и $d{${generic_name}} соответственно
        # Для подробностей см. раздел 'Экстраполяция значений в описании тестового окружения'
```

##### Установка значений параметров в командной строке
При запуске проверки с помощью скрипта --...-- значения требуемых параметров тестового окружения указыаются следующим образом:
`  -g=<generic_1_name>:<generic_1_value> -g=<generic_2_name>:<generic_2_value> ...`\
Для параметров, которые должны быть типа `list` или `dict` в качестве значения передаётся выражение
`$e{<строковое представление списка или словаря в языке Python>}`
  
Использование параметров тестового окружения описано как часть следующего раздела

#### Экстраполяция значений в описании тестового окружения

При указании значений в описании тестового окружения есть возможность указывать не конкретное значение, а ссылаться
на значение другого параметра в описании этого же тестового окружения а так же использовать выражения Python.

К примеру:
```yaml
condition: "${generic_name}" # В качестве значения для параметра condition будет использовано значение параметра
                             # тестового окружения с именем 'generic_name' (д.б. описан в секции generics тестового окружения)
```

##### Формат описания:

Экстраполяция осуществляется только для строковых значений. Значения, соответствующие регулярному выражению `\$\w?{.+?}`
(инмеуемые далее как 'экстраполируемые выражения') будт замещаться в соответствии с приведёнными ниже правилами.

##### Правила экстраполяции

Выражения подстановки:
* `${<generic_name>}` и `$generics.{<generic_name>}` - используется для подстановки значения параметра тестового 
окружения с указанным именем `generic_name`
* `${alias.<alias_name>}` - используется для подстановки значения псевдонима с указанным именем `alias_name`
* `${<entity_name>.<field_name>}` - используется для подстановки значения параметра с именем `field_name` из сущности с 
именем `entity_name`
* `$e{<expression>}` - используется для подстановки результата выражения Python, указанного внутри фигурных скобок. 
В том числе используется для приведения строковых значений к другим типам Python, которые не поддержаны выражениями ниже

Выражения приведения типов:
* `$b{<value>}` - приведение содержимого фигурных скобок к типу `bool`. Строковые значения 'True' и 'False' трактуются 
соответственно как True и False, для других значений используются правила приведения типов Python
* `$i{<value>}` - приведение содержимого фигурных скобок к типу `int`. Используются правила приведения типов Python
* `$f{<value>}` - приведение содержимого фигурных скобок к типу `float`. Используются правила приведения типов Python
* `$s{<value>}` - приведение содержимого фигурных скобок к типу `string`. Используются правила приведения типов Python
* `$l{<value>}` - приведение содержимого фигурных скобок к типу `list`. Значение должно быть строковым представением 
списка в соответстии с правилами Python -- TODO: --
* `$d{<value>}` - приведение содержимого фигурных скобок к типу `dict`. Значение должно быть строковым представением 
словаря в соответстии с правилами Python -- TODO: --

_*Примечание:* Угловые скобки использованы для обозначения --переенного-- значения в описании правила, и не требуеют реальной 
подстановки их в тексте_

##### Приведение типов

При подстановке значения если экстраполируемое выражение не является полным значением строки или если 
тип подставляемого значения для выржений, кроме выражений приведения типов, не bool, int, float, то будет подставлено 
его текстовое представление в соответствии с правилами Python

Для приведения итогового значения к нужному типу завершающим выражением (таким, которое начинается в начале строки и 
закнчивается в её конце) следует испольлзовать выражения приведения к типу или подстановки выражения Python

При использовании `$e{<expression>}` нельзя проконтролировать, что результирующее значение окажется нужного типа

##### Порядок экстраполяции выражений:

Допускается иметь несколько экстраполируемых выражений в одной строке, в т.ч. вложенных друг в друга.\
Кроме этого допускается что после экстарполяции одного из них сформируется новое экстраполируемого выражение,
например `${${generic_name_1}.${generic_name_2}}` - после экстраполяции `${generic_name_1}` и `${generic_name_2}` может 
сформироваться новое экстраполируемое выражение вида `${<entity_name>.<field_name>}`.
При этом не обхоидмо избегать циклических ссылок. При наличии циклических ссылок выполнение проверки будет 
прервано.

Значения параметров тестового окружения (секция `generics`) так же могут экстраполироваться, но только используя 
значения других параметров тестового окружения, выражения Python и приведения типов, без использования параметров 
сущностей.

В первую очередь осуществляется экстраполяция значений параметров тестового окружения
После этого осуществляется экстраполяция всех остальных параметров

При экстраполяции каждого значения используется следующий принцип:
1. Пока возможна подстановка значений параметров тестового окружения или других сущностей, она осуществляется
2. Выполняется экстраполяция выражения Python
3. Если появляется возможность подстановки параметров тестового окружения или других сущностей, повторяются действия
начиная с п.1
4. Если есть возможность эктраполяции выражения Python, повторяются действия начиная с п.2
5. Производится приведение типа, если такое имеется

##### Примеры экстраполируемых значений

Строка со значением `${mock}` - будет заменена на значение параметра тестового окружения с именем `mock`
Если тип параметра int, то в итоге экстраполяции данной строки будет значение с типом int и т.д.\

В строке  `is ${mock}` - будет произведена заменена её части `${mock}`на значение параметра тестового окружения с именем
 `mock`, при этом будет подставлено его строковое представление.

Строка со значением `$e{${mock} == 1}` - будет заменена на `True` типа `bool`, если значение параметра mock это 
целое число со значением `1`, число с плавающей запятой и значением `1.0`, а так же строка со значениями `1`, ` 1`,
 ` 1. `, `   1.0000   ` и т.д. (пробелы вокруг значения, знак запятой (`.`) а так же 0 после запятой), 
 в противном случае она будет заменена на `False` типа `bool`

#### Секция alias

Содержит список псведонимов, которые могут быть использовны для подставноки при экстраполяции значений

Эта секция позволяет описывать общие экстраполируеме выражения и константы для того, чтобы ссылаться на них в других 
частях описания

В псевдониме в т.ч. может быть экстраполируемое выражение, использующее другой псведоним, но необхоидмо избегать 
циклических ссылок. При наличии циклических ссылок выполнение проверки будет прервано.

В некотором смысле эта секция подобна секции `generics`, но значения её параметров нельзя задать в командной строке

##### Формат описания
```yaml
      alias: # Содержит структуру с перечнем псевдонимов и их значениями
        # Имя поля - имя параметра, значение поля - значение параметра по умолчанию
        # Допустимые типы параметров: string, int, float, list, dict
        <alias_1_name>: <alias_1_default_value>
        <alias_2_name>: <alias_2_default_value>
```

#### Секция 'include'

-- TODO: требуется проработка и реализация --
Секция относится к расширению описания иерархии сущностей.

Блок данной секции повзоляет включить на уровне текста без какого либо анализа содержимое другого файла YAML. 
При велючении текста будет учтён текущий уровень отступов.

##### Формат описания
```yaml
      include: # Содержит путь к описанию включаемого текста и параметры его включения
        path: <path_to_test_env>
        auth_name: <auth_name>  # Имя для аутентификции при доступе через URI   -- TODO: проработать вопрос использования --
        auth_key: <auth_key>    # Ключ для аутентификции при доступе через URI  -- TODO: проработать вопрос безопасноти --
        condition: <condition>  # Условие включения (аналогично применению в описании сущности)
```

#### Секция 'subenv'

Секция относится к расширению описания иерархии сущностей.

Блок данной секции позволяет включить тестовое окружение, описанное в другом файле в качестве части данного тестового 
окружения.

-- TODO: требуется реализовать --

##### Формат описания
```yaml
      subenv: # Содержит путь к описанию включаемого тестовое окружения и параметры его включения
        # Путь может быть абсолютным, относительным, в формате URI. В качестве разделителя в пути используется символ `/`
        path: <path_to_test_env>
        auth_name: <auth_name>  # Имя для аутентификции при доступе через URI   -- TODO: проработать вопрос использования --
        auth_key: <auth_key>    # Ключ для аутентификции при доступе через URI  -- TODO: проработать вопрос безопасноти --
        name: <env_name>        # Имя включаемого тестового окружения из файла описания
        
        # Точка включения
        platform: <root_entity_name>  # Задаёт родительскую сущность для включаемого тестового окружения в том случае,
                                      # если секция subenv находится в верху иерархии сущснотей
        
        # Параметры включаемого тестового окружения
        generics:
          <generic_1_name>: <generic_1_value>  # Ключ - имя параметра включаемого тестового окружения
          <generic_2_name>: <generic_2_value>  # Значение - устанавливаемое значение соответствующего параметра
        ...
        # Параметры альтерации имён сущностей
        name_prefix: <name_prefix_value>  # Постоянный префикс, приставляемый к имени сущностей тестового окружения
        name_suffix: <name_suffix_value>  # Постоянный суффикс, приставляемый к имени сущностей тестового окружения
        
        channels:                     # Список каналов сообщений, на которые должны быть подписаны все включаемые сущности
          - "<channel_1_name>"
          - "<channel_2_name>"

        wait:                         # Список имён сущностей, трубемых для работы включаемых.
          - "entity_1_name"
          - "entity_2_name"
        
        # Параметры исключения сущностей из импортируемого тестового окружения
        exclude:
          platform: # Исключение сущностей по типу
            - "sequencer"
          name:     # Исключение сущностей по имени. NOTE: Вместо имени м.б. использованы и другие поля
            - "$e{re.search('sequencer')}"
                
        # Условие включения (аналогично применению в описании сущности)
        condition: <condition>
```

##### Принцип действия

Создаёт иерархию сущностей указанного тестового окружения и включает её в данное тестовое окружение

Для исключения пересечения имён сущностей, к именам включаемого тестового окружения можно приставлять префксы и суффииксы

Если секция `subenv` имеет родительскую сущность (при иерархическом способе описания), то она будет родительской и для
 включаемой иерархии, иначе (если секция `subenv` находится в верху иерархии сущностей тестового окружения), то если
  указан параметр platform и его значение не пустая строка и не None, то родителем для включаемой иерархии будет 
  указанная в этом параметре сущность, в противном случае включаемая иерархия будет подключена к корню тестового окружения

#### Секция 'generate'

Секция относится к расширению описания иерархии сущностей

Данная секция позволяет сгенерировать сущности на основании описания итератора и шаблона описания иерархии сущснотей 

##### Формат описания
```yaml
      generate: # Содержит структуру с перечнем псевдонимов и их значениями
        iterator: "<Python iterable expression>"  # Выражение Python, возвращающее итерируемый объект (список, генератор range и т.п.)
        iterator_name: <iterator_name_value>      # Имя итератора, строковое значение
        condition: <condition>                    # Условие использования генератора (аналогично применению в описании сущности)
        # Опциональные параметры альтерации имён генерируемых сущнотей
        name_prefix: <name_prefix_value>          # Постоянный префикс, приставляемый к имени сущностей из шаблона  -- TODO: --
        name_suffix: <name_suffix_value>          # Постоянный суффикс, приставляемый к имени сущностей из шаблона  -- TODO: --
        platforms: # Шаблон описания иерархии сущностей. Формат содержимого соответствует формату описания иерархии сущностей
          <entity_type_A>:  # Тип описываемой сущности
            # Строка с именем данной сущности должна содердать выражение ${<iterator_name>}, которое будет заменяться 
            # значением итератора чтобы имена генерируемых сущности отличались
            # Это можно задавать с помощью параетров name_prefix и name_suffix (в них должно содержаться выражение ${<iterator_name_value>})
            # Или путём вставки этого выражения явным образом в имена сущностей в шаблоне (пример ниже)
            - name: "<entity_1_name_prefix>${<iterator_name_value>}<entity_1_name_suffix>"
              # Для примера приведено, что значение итератора может быть подставлено в другие параметры сущности 
              condition: "$e{${'<iterator_name_value>'=='x1'}" 
            ...            
            - name: "<entity_2_name_prefix>${<iterator_name>}<entity_2_name_suffix>"
            ...
```

##### Принцип действия
Для каждого значения итератора формируется набор сущностей в соовтетствии с указанным шаблоном.
В строковых параметрах сущностей выражение `${<iterator_name_value>}`, где `<iterator_name_value>` это значение
параметра `iterator_name`, будет заменено на строковое представление значения итератора текущей итерации.

Родителем сущностей "верхушки" иерархии в шаблоне будет родительская сущность секции generate, если такая имеется, 
иначе будет назначена в соответствии со значением параметра `platform` эттих сущностей, для оставльных сущностей
родитель будет назначаться по стандатным правилам -- TODO: убедиться что так --

##### Содержимое шаблона описания иерархии

В шаблоне описания иерархии м.б. как описания сущностей, так и секции `group`, `innclude`, `subenv` а так же `generate`.

ВАЖНО чтобы значение итератора подставлялось ВО ВСЕ имена генерируемых сущностей, т.е.
`${<iterator_name_value>}` должен быть в именах сущснотей, в именах сущностей в шаблоне вложенной секции `generate`,
в параметре префикса или суффикса имени секции `subenv`.

Для упрощения этой задачи можно использовать параметры `name_prefix` или `name_suffix` и включить в них 
`${<iterator_name_value>}`.

Если в секции будет вложенна другая секция `generate` или `group`, то суффиксы и префикмы будутт добавляться в следующем порядке:\
`<перфикс уровня 1><перфикс уровня 2>...<значение имени из параметра сущности><суффикс уровня 1><суффикс уровня 2>...`

#### Секция 'group'

Данная секция позволяет сгруппировать несколько сущснотей для того, чтобы задать им общие свойства.

Может быть полезной в сочетании с секцией generate, а так же для включения/отключения группы сущностей из тестового 
окружения.

-- TODO: требуется реализовать --

##### Формат описания
```yaml
      group: # Содержит описания группируемых сущностей и правила применения общих параметров
        condition: <condition>        # Условие включения всей группы (аналогично применению в описании сущности)

        # Общие параметры сущностей в группе. Задают значение параметров по умолчанию 
        # Т.е. будут действовать, если не будут указаны явно в описании сущности
        generics:
          <generic_1_name>: <generic_1_value>  # Ключ - имя общего параметра сущностей
          <generic_2_name>: <generic_2_value>  # Значение - устанавливаемое значение соответствующего параметра
          
        # Префиксы для общих параметров сущностей в группе. Добавляются к значению указанного параметра сущности
        # Будут добавлены как для значений по умолчанию, так и для указаннных в сущноти явным образом
        generics_prefixes:
          <generic_1_name>: <generic_1_prefix_value>  # Ключ - имя общего параметра сущностей
          <generic_2_name>: <generic_2_prefix_value>  # Значение - префикс, добавлямеый к значению соответствующего параметра

        # Суффиксы для общих параметров сущностей в группе. Добавляются к значению указанного параметра сущности
        # Будут добавлены как для значений по умолчанию, так и для указаннных в сущноти явным образом
        generics_suffixes:
          <generic_1_name>: <generic_1_suffix_value>  # Ключ - имя общего параметра сущностей
          <generic_2_name>: <generic_2_suffix_value>  # Значение - префикс, добавлямеый к значению соответствующего параметра
        
        platforms: # Содержит описание иерархии сущностей в группе, формат аналогичен описанию такой иерархии в тестовом окружении
```

##### Порядок применения префиксов и суффиксов при вложенности

Если в секции будет вложенна другая секция `group` или `generate`, то суффиксы и префикмы будутт добавляться в следующем порядке:\
`<перфикс уровня 1><перфикс уровня 2>...<значение имени из параметра сущности><суффикс уровня 1><суффикс уровня 2>...`

#### Секция 'platforms'

Секция зарезервирована для явного отделения описания иерархии сущностей от параметров тестового окружения
-- TODO: --

#### Extension

Секция зарезервирована для расширения правил описания без нарушения обратной совместимости. Будет использована
при бэкпортировании новых возможностей в старые версии

#### Model

Секция зарезервирована для описания абстрактной модели, которую реализует описанная иерархия сущностей
-- TODO: --