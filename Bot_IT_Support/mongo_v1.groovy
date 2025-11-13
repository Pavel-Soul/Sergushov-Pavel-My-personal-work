{
  $jsonSchema: {
    bsonType: 'object',
    required: [
      'ReqNumb',
      'ReqText',
      'ReqStartDt',
      'CreatorUserId',
      'Status'
    ],
    properties: {
      ReqNumb: {
        bsonType: 'int',
        description: 'Уникальный номер заявки'
      },
      ReqText: {
        bsonType: 'string',
        description: 'Текст заявки'
      },
      ReqStartDt: {
        bsonType: 'date',
        description: 'Дата создания заявки'
      },
      CreatorUserId: {
        bsonType: 'string',
        description: 'ID создателя заявки'
      },
      Status: {
        bsonType: 'string',
        'enum': [
          'Создана',
          'В работе',
          'Выполнено'
        ],
        description: 'Статус заявки'
      }
    }
  }
}