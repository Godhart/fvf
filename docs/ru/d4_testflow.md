# Порядок выполнения проверки

## Запуск проверки

Проверка запускается с помощью скрипта Python `run_test.py`, находящегося в папке src.

Формат вызова скрипта:
```
python run_test.py <environment> <tests package>  
         [<tests module>] [<tests class>] [<test name>] [<start_stop>]
         [<options>]
```

Аргументы вызова скрипта:
```
  environment   - path to file with environment description or string with decription itself
  tests package - name of package from src/tests which contains module with necessary test(s)
  tests module  - name of module from test_package with necessary test(s). By default it's 'main'
  tests class   - class name from module main with necessary test(s) description. By default it's 'RootTest'
  test name     - name of test to run. If not specified then all tests contained in test class would run
  start_stop    - specify value as 'start_stop', 'True' or '1' to start and stop entities between tests. 'False' by default

Following one or more options could passed along:

Test environment options:

  -g=<generic name>:<generic value>   - specifies test environment generics, one per each generic. 
    Generic name should be alphanumeric value.  
    Generic value could be a string or quoted string. See NOTE below about values types conversion.

Test options:

  -a=<argument value>  - specifies positional arguments for test class constructor, one per each argument
    Argument value could be a string or quoted string. See NOTE below about value types conversion
  
  -k=<argument name>:<argument value> - specifies keyworded arguments for test class constructor, one per each argumet
    Argument value could be a string or quoted string. See NOTE below about values types conversion

Result output options:

  -re   -  report elapsed time in tests results

Verbose output options:  

  -h    -  don't run test, print this usage information only

  -v    -  turn on verbose output
  -vf   -  direct verbose output into file '.log' in working directory
  -ve   -  print errors output into verbose output stream
  
NOTE: Values conversion. 

  Values of test environment's generics and arguments for test class constructor would be converted as following:
  'True' or 'False' would be converted to boolean type,
  Values with digits only would be converted to integer number type, 
  Digits with single point would be converted to float number type. 
  
  If other type is desired use string with following template: $e{<python expression>}.
  Resulting type would be return type of python expression.
  For constructor arguments inside curly braces shall be only valid python expression.
  For generics values more complicated expression allowed, for more information read about test environment's 
  values extrapolation.
```


## Загрузка описания тестового окружения

После запуска скрипта проверки на первом этапе осуществляется загрузка описания тестового окружения.

Загрузка происходит следующим образом:

1. Загружается текст описания тествого окружения, указанного в параметрах запуска
2. Осуществляется экстраполяция значений
3. Осуществляется загрузка содержимого секций `include`
4. Шаги 2-3 повторяются пока содержимое пока в описании на 3-м шаге больше не будет секций `include`.
 При этом контролируется отсутсвие зацикленности. При обнаружении зацикленности проверка прерывается
5. Осуществляется генерация содержимого секций `generate`
6. Осуществляется загрузка описаний тестовых окружений секций `import` и включение их содержимого в текущее тестовое
окружение. Загрузка описания тестового окружения из каждой секции `import` осуществляется изолированно от других и от 
текущего, выполняя описанные в этом пункте шаги 1-6. При загрузке контролируется отсутсвие зацикленности. 
При обнаружении зацикленности проверка прерывается

## Интсанцинация

В соответствии с загруженным описанием тествого окружения создаются объекты тестового окружения.

Объекты создаются в следующем порядке: объект тестового окружения создаётся, если для него не предполагается родительский
объект или он уже создан, а так же если созданы объекты тестового окружения из списка ожидания этого объекта.

В случае, если после завершения создания всех объектов, для которых были выполнены эти условия, некоторые объекты так и 
не были созданы, проверка прерывается.

## Запуск тестов

### Запуск объектов тестового окружения

На этом этапе обекты абстракции сущностей устанавливают связь с ассоциированными с ними сущностями, приводят 
их в исходное состояние или синхронизируют своё состояние с их состоянием.

Прочие объекты тестового окружениия выполняют необходимые действия, требуемые для их работы, в т.ч. могут 
загружать результаты прежних проверок, занимать требуемые ресурсы (открывать сокет и т.п.).

В зависимости от значения переданного параметра start_stop, запуск объектов может производиться как единоразово
перед проведенеим всех тестов, так и постоянно перед запуском очередного теста.

Запуск объектов тестового окружения осуществляется в том же порядке, что и их создание.

На этапе запуска объекты могут выполнять запросы к другим объектам. Объекты к которым будут выполняться запросы должны 
быть либо родительскими, либо быть в списке ожидания объекта, формирующего запрос.

### Выполнение теста



### Остановка объектов тестового окружения

На этом этапе разрывается связь объектов абстракции с ассоциированными с ними сущностьями, при необходиомсти сохраняются 
результаты проверки другими объектами тестового окружения, а так же при выгружается котекст и освобождаются занимаемые 
ресурсы (память, сокет и т.п.).

## Завершение

--TODOC:--

