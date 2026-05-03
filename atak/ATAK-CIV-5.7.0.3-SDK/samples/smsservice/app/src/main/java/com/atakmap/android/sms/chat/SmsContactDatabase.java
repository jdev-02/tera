package com.atakmap.android.sms.chat;

import com.atakmap.android.contact.IndividualContact;
import com.atakmap.android.contact.SmsConnector;
import com.atakmap.database.DatabaseIface;
import com.atakmap.database.Databases;
import com.atakmap.database.StatementIface;
import com.atakmap.database.QueryIface;

import java.util.ArrayList;
import java.util.List;

import gov.tak.api.contact.IContact;
import gov.tak.api.contact.IContactListener;
import gov.tak.api.contact.IContactService;
import gov.tak.api.util.Disposable;

public class SmsContactDatabase implements IContactService, Disposable {
    DatabaseIface database;
    
    public SmsContactDatabase(String path) {
        database = Databases.openDatabase(path, false);
        if(Databases.getTableNames(database).isEmpty())
            database.execute("CREATE TABLE contacts (uid TEXT PRIMARY KEY, name TEXT, address TEXT)", null);
    }
    
    @Override
    public void addContact(IContact contact) {
        if(!(contact instanceof IndividualContact))
            return;
        IndividualContact smsContact = (IndividualContact)contact;
        StatementIface stmt = null;
        try {
            stmt = database.compileStatement("INSERT INTO contacts (name, address, uid) VALUES(?, ?, ?)");
            stmt.bind(1, smsContact.getName());
            stmt.bind(2, smsContact.getConnector(SmsConnector.CONNECTOR_TYPE).getConnectionString());
            stmt.bind(3, smsContact.getUid());
            stmt.execute();
        } finally {
            if(stmt != null)
                stmt.close();
        }
    }

    @Override
    public void updateContact(IContact contact) {
        if(!(contact instanceof IndividualContact))
            return;
        IndividualContact smsContact = (IndividualContact)contact;
        StatementIface stmt = null;
        try {
            stmt = database.compileStatement("UPDATE contacts SET name = ?, address = ? WHERE uid = ?");
            stmt.bind(1, smsContact.getName());
            stmt.bind(2, smsContact.getConnector(SmsConnector.CONNECTOR_TYPE).getConnectionString());
            stmt.bind(3, smsContact.getUid());
            stmt.execute();
        } finally {
            if(stmt != null)
                stmt.close();
        }
    }

    @Override
    public void removeContact(String uid) {
        StatementIface stmt = null;
        try {
            database.compileStatement("DELETE FROM contacts WHERE uid = ?");
            stmt.bind(1, uid);
            stmt.execute();
        } finally {
            if(stmt != null)
                stmt.close();
        }
    }

    @Override
    public IContact getContact(String uid) {
        try(QueryIface result = database.compileQuery("SELECT name, address FROM contacts WHERE uid = ? LIMIT 1")) {
            result.bind(1, uid);
            return result.moveToNext() ? new SmsContact(result.getString(1)) : null;
        }
    }

    @Override
    public List<IContact> getAllContacts() {
        try(QueryIface result = database.compileQuery("SELECT uid, name, address FROM contacts")) {
            ArrayList<IContact> contacts = new ArrayList<>();
            while(result.moveToNext()) {
                contacts.add(new SmsContact(result.getString(2)));
            }
            return contacts;
        }
    }

    @Override
    public void registerContactListener(IContactListener contactListener) {

    }

    @Override
    public void unregisterContactListener(IContactListener contactListener) {

    }

    @Override
    public void dispose() {
        database.close();
    }
}
