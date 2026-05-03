package com.atakmap.android.test;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;


import android.content.Context;
import android.content.SharedPreferences;
import android.location.Location;
import android.os.Environment;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.preference.AtakPreferences;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoCalculations;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;

import org.junit.After;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.MockitoJUnitRunner;


import java.io.File;

/**
 * Tests the GRGPrefs Class
 */
@RunWith(MockitoJUnitRunner.Silent.class)
public class ExampleGeoPointTest {

    /**
     * The Atak preferences mock.
     */
    @Mock
    AtakPreferences atakPreferencesMock;

    /**
     * Holds the mocked SharedPreferences
     */
    @Mock
    private SharedPreferences sharedPreferencesMock;

    /**
     * Context Mock
     */
    @Mock
    private Context contextMock;


    private MockedStatic<Log> logStatic;
    private MockedStatic<Location> locationStatic;
    private MockedStatic<Environment> environmentStatic;
    private MockedStatic<FileSystemUtils> fileSystemUtilsStatic;
    private MockedStatic<MapView> mapViewStatic;
    private MockedStatic<AtakPreferences> atakPreferencesStatic;
    private MockedStatic<GeoCalculations> geoCalculationsStatic;

    /**
     * Runs before each test.
     */
    @Before
    public void setUp() {
        //Required for Logging
        logStatic = Mockito.mockStatic(Log.class);
        environmentStatic = Mockito.mockStatic(Environment.class);
        locationStatic = Mockito.mockStatic(Location.class);
        //Required for mocking MapView
        fileSystemUtilsStatic = Mockito.mockStatic(FileSystemUtils.class);
        File fileMock = Mockito.mock(File.class);
        Mockito.when(fileMock.getAbsolutePath()).thenReturn("filePath");
        Mockito.when(FileSystemUtils.getItem(anyString())).thenReturn(fileMock);
        //Required for creating AtakPreference class
        mapViewStatic = Mockito.mockStatic(MapView.class);
        MapView mapViewMock = Mockito.mock(MapView.class);
        contextMock = Mockito.mock(Context.class);
        Mockito.when(mapViewMock.getContext()).thenReturn(contextMock);
        Mockito.when(MapView.getMapView()).thenReturn(mapViewMock);
        Mockito.when(mapViewMock.isContinuousScrollEnabled()).thenReturn(true);

        atakPreferencesStatic = Mockito.mockStatic(AtakPreferences.class);
        Mockito.when(atakPreferencesMock.getSharedPrefs()).thenReturn(sharedPreferencesMock);
        Mockito.when(AtakPreferences.getInstance(any())).thenReturn(atakPreferencesMock);

        geoCalculationsStatic = Mockito.mockStatic(GeoCalculations.class);
        Mockito.when(GeoCalculations.pointAtDistance(any(), any(double.class), any(double.class))).thenReturn(new GeoPoint(40, -82));
    }

    /**
     * Runs after each test.
     */
    @After
    public void tearDown() {
        logStatic.close();
        locationStatic.close();
        fileSystemUtilsStatic.close();
        atakPreferencesStatic.close();
        mapViewStatic.close();
        environmentStatic.close();
        geoCalculationsStatic.close();
    }

    /**
     *  SimpleTest
     */
    @Test
    public void testReturn() {
        MapView mapView = MapView.getMapView();
        Mockito.when(mapView.getCenterPoint()).thenReturn(new GeoPointMetaData(new GeoPoint(60.00000, 170.00000)));
        Assert.assertEquals(60, mapView.getCenterPoint().get().getLatitude(), .001);
    }
}